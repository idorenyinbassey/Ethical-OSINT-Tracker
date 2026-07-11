from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.repositories.api_config_repository import get_all_configs, create_or_update_config
from app.repositories.user_repository import update_password, get_by_id
from app.utils.validators import validate_base_url
from functools import wraps

ph = PasswordHasher()

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


def admin_required(f):
    """Decorator to require admin user for a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
            abort(403)
        return f(*args, **kwargs)
    return decorated

SERVICES = [
    # Free sources (no API key needed)
    {"name": "TorProxy", "label": "Tor / Proxy (SOCKS5 or HTTP)", "default_url": "socks5://127.0.0.1:9050"},
    # Optional enrichment APIs
    {"name": "IPInfo", "label": "IPInfo.io (optional — ip-api.com is used free by default)", "default_url": "https://ipinfo.io"},
    {"name": "Shodan", "label": "Shodan (port scans & CVEs)", "default_url": "https://api.shodan.io"},
    {"name": "VirusTotal", "label": "VirusTotal (threat intelligence)", "default_url": "https://www.virustotal.com/api/v3"},
    {"name": "HIBP", "label": "Have I Been Pwned (breach data)", "default_url": "https://haveibeenpwned.com/api/v3"},
    {"name": "Hunter.io", "label": "Hunter.io (email deliverability)", "default_url": "https://api.hunter.io/v2"},
    {"name": "NumVerify", "label": "NumVerify (phone validation)", "default_url": "http://apilayer.net/api"},
    {"name": "ImageRecognition", "label": "Google Cloud Vision (AI image analysis)", "default_url": "https://vision.googleapis.com/v1"},
    {"name": "IMEIService", "label": "IMEI Service", "default_url": "https://api.imei.info"},
]


@settings_bp.route("/")
@login_required
def index():
    # Non-admins can only see password change form
    if not current_user.is_admin:
        return render_template("settings/index.html", services=[], configs={})

    # Admins can see all API configurations
    configs = {c.service_name: c for c in get_all_configs()}
    return render_template("settings/index.html", services=SERVICES, configs=configs)


@settings_bp.route("/save", methods=["POST"])
@login_required
@admin_required
def save():
    """Save API configuration. Admin-only to prevent key/URL tampering.

    Validates base URLs to prevent SSRF attacks. Encrypts API keys before storage.
    """
    service_name = request.form.get("service_name", "")
    api_key = request.form.get("api_key", "").strip()
    base_url = request.form.get("base_url", "").strip()
    is_enabled = request.form.get("is_enabled") == "on"
    notes = request.form.get("notes", "").strip()

    if not service_name:
        flash("Service name is required.", "error")
        return redirect(url_for("settings.index"))

    # Validate base URL to prevent SSRF attacks
    if base_url:
        is_valid, error_msg = validate_base_url(base_url)
        if not is_valid:
            flash(f"Invalid base URL: {error_msg}", "error")
            return redirect(url_for("settings.index"))

        # Warn if HTTP is used with API key (should be HTTPS)
        if base_url.startswith("http://") and api_key:
            flash(
                f"{service_name} uses HTTP (not HTTPS) — API key is exposed in transit. "
                "Consider using HTTPS instead.",
                "warning"
            )

    create_or_update_config(
        service_name=service_name,
        api_key=api_key,
        base_url=base_url,
        is_enabled=is_enabled,
        notes=notes,
    )
    flash(f"{service_name} settings saved by admin.", "success")
    return redirect(url_for("settings.index"))


@settings_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    current_pw = request.form.get("current_password", "")
    new_pw = request.form.get("new_password", "")
    confirm_pw = request.form.get("confirm_password", "")

    user = get_by_id(current_user.id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("settings.index"))

    try:
        ph.verify(user.password_hash, current_pw)
    except VerifyMismatchError:
        flash("Current password is incorrect.", "error")
        return redirect(url_for("settings.index"))

    if len(new_pw) < 6:
        flash("New password must be at least 6 characters.", "error")
        return redirect(url_for("settings.index"))

    if new_pw != confirm_pw:
        flash("New passwords do not match.", "error")
        return redirect(url_for("settings.index"))

    update_password(current_user.id, ph.hash(new_pw))
    from app.utils.audit import log as audit_log
    audit_log("account.password_change", entity_type="user", entity_id=current_user.id)
    flash("Password changed successfully.", "success")
    return redirect(url_for("settings.index"))
