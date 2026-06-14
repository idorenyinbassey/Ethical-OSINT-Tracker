from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
from app.repositories.api_config_repository import get_all_configs, create_or_update_config

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
    {"name": "IMEIService", "label": "IMEI Service", "default_url": "https://api.imei.info"},
]


@settings_bp.route("/")
@login_required
def index():
    configs = {c.service_name: c for c in get_all_configs()}
    return render_template("settings/index.html", services=SERVICES, configs=configs)


@settings_bp.route("/save", methods=["POST"])
@login_required
def save():
    service_name = request.form.get("service_name", "")
    api_key = request.form.get("api_key", "").strip()
    base_url = request.form.get("base_url", "").strip()
    is_enabled = request.form.get("is_enabled") == "on"
    notes = request.form.get("notes", "").strip()

    if not service_name:
        flash("Service name is required.", "error")
        return redirect(url_for("settings.index"))

    create_or_update_config(
        service_name=service_name,
        api_key=api_key,
        base_url=base_url,
        is_enabled=is_enabled,
        notes=notes,
    )
    flash(f"{service_name} settings saved.", "success")
    return redirect(url_for("settings.index"))
