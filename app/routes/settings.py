from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.repositories.api_config_repository import get_all_configs, create_or_update_config
from app.repositories.user_repository import (
    update_password, get_by_id, set_totp_secret, enable_totp, disable_totp, set_recovery_codes,
)
from app.repositories.api_key_repository import create_api_key, list_active_keys, revoke_key
from app.utils.validators import validate_base_url
from app.utils.decorators import admin_required
from app.utils.crypto import encrypt_secret, decrypt_secret
from app.utils import totp as totp_utils

ph = PasswordHasher()

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

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
    {"name": "TinEye", "label": "TinEye (reverse image search — requires paid TinEye account)", "default_url": "https://api.tineye.com"},
    {"name": "IMEIService", "label": "IMEI Service", "default_url": "https://api.imei.info"},
    # Outbound alerting
    {"name": "Notifications", "label": "Notifications — webhook on watchlist change (ntfy.sh, Discord, Slack, etc.)", "default_url": ""},
]


@settings_bp.route("/")
@login_required
def index():
    api_keys = list_active_keys(current_user.id)
    # Non-admins can only see password change + their own API keys
    if not current_user.is_admin:
        return render_template("settings/index.html", services=[], configs={}, api_keys=api_keys)

    # Admins can see all API configurations
    configs = {c.service_name: c for c in get_all_configs()}
    return render_template("settings/index.html", services=SERVICES, configs=configs, api_keys=api_keys)


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


# ── Personal API keys (for /api/v1) ────────────────────────────────────────────

@settings_bp.route("/api-keys/create", methods=["POST"])
@login_required
def create_api_key_route():
    label = request.form.get("label", "").strip()[:100]
    key, raw_key = create_api_key(current_user.id, label=label)
    from app.utils.audit import log as audit_log
    audit_log("apikey.created", entity_type="apikey", entity_id=key.id, detail=label)
    flash(
        f"API key created. Copy it now — it will not be shown again: {raw_key}",
        "success",
    )
    return redirect(url_for("settings.index"))


@settings_bp.route("/api-keys/<int:key_id>/revoke", methods=["POST"])
@login_required
def revoke_api_key_route(key_id):
    if revoke_key(key_id, user_id=current_user.id):
        from app.utils.audit import log as audit_log
        audit_log("apikey.revoked", entity_type="apikey", entity_id=key_id)
        flash("API key revoked.", "success")
    else:
        flash("API key not found.", "error")
    return redirect(url_for("settings.index"))


# ── Two-factor authentication (TOTP) ────────────────────────────────────────────

def _qr_data_uri(uri: str) -> str:
    import io, base64
    import qrcode
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@settings_bp.route("/2fa")
@login_required
def two_factor():
    user = get_by_id(current_user.id)
    if user.totp_enabled:
        return render_template("settings/2fa.html", enabled=True)

    # Generate (and persist, encrypted) a pending secret if none exists yet,
    # so reloading this page before scanning the QR shows the same code
    # rather than silently invalidating it.
    if not user.totp_secret:
        secret = totp_utils.generate_secret()
        set_totp_secret(current_user.id, encrypt_secret(secret))
    else:
        secret = decrypt_secret(user.totp_secret)

    qr_data_uri = _qr_data_uri(totp_utils.provisioning_uri(secret, user.username))
    return render_template("settings/2fa.html", enabled=False, secret=secret, qr_data_uri=qr_data_uri)


@settings_bp.route("/2fa/confirm", methods=["POST"])
@login_required
def two_factor_confirm():
    user = get_by_id(current_user.id)
    if user.totp_enabled or not user.totp_secret:
        flash("Start the 2FA setup again.", "error")
        return redirect(url_for("settings.two_factor"))

    code = request.form.get("code", "").strip()
    secret = decrypt_secret(user.totp_secret)
    if not totp_utils.verify_code(secret, code):
        flash("Invalid code — check your authenticator app and try again.", "error")
        return redirect(url_for("settings.two_factor"))

    codes = totp_utils.generate_recovery_codes()
    set_recovery_codes(current_user.id, totp_utils.hash_recovery_codes(codes))
    enable_totp(current_user.id)
    from app.utils.audit import log as audit_log
    audit_log("account.2fa_enabled", entity_type="user", entity_id=current_user.id)
    return render_template("settings/2fa_recovery_codes.html", codes=codes)


@settings_bp.route("/2fa/regenerate-codes", methods=["POST"])
@login_required
def two_factor_regenerate_codes():
    user = get_by_id(current_user.id)
    if not user.totp_enabled:
        flash("2FA is not enabled.", "error")
        return redirect(url_for("settings.two_factor"))

    codes = totp_utils.generate_recovery_codes()
    set_recovery_codes(current_user.id, totp_utils.hash_recovery_codes(codes))
    from app.utils.audit import log as audit_log
    audit_log("account.2fa_recovery_regenerated", entity_type="user", entity_id=current_user.id)
    return render_template("settings/2fa_recovery_codes.html", codes=codes)


@settings_bp.route("/2fa/disable", methods=["POST"])
@login_required
def two_factor_disable():
    password = request.form.get("password", "")
    user = get_by_id(current_user.id)
    try:
        ph.verify(user.password_hash, password)
    except VerifyMismatchError:
        flash("Incorrect password.", "error")
        return redirect(url_for("settings.two_factor"))

    disable_totp(current_user.id)
    from app.utils.audit import log as audit_log
    audit_log("account.2fa_disabled", entity_type="user", entity_id=current_user.id)
    flash("Two-factor authentication disabled.", "success")
    return redirect(url_for("settings.index"))
