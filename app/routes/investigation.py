import json
import os
from pathlib import Path

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.repositories.investigation_repository import create_investigation, list_recent
from app.repositories.case_repository import list_cases
from app.services import (
    ip_client, rdap_client, hibp_client, hunter_client,
    numverify_client, social_client, image_client, imei_client,
    virustotal_client, shodan_client,
)

investigation_bp = Blueprint("investigation", __name__, url_prefix="/investigate")

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"}
ALLOWED_FILE_EXTENSIONS = {
    "jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp",
    "mp3", "flac", "wav", "ogg", "aac", "m4a", "wma",
    "mp4", "avi", "mov", "mkv", "wmv", "flv", "webm",
    "pdf", "docx", "xlsx", "xls",
}


def _ext_ok(filename: str, allowed: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def _cases_for_select():
    return list_cases()


# ── index ────────────────────────────────────────────────────────────────────

@investigation_bp.route("/")
@login_required
def index():
    return render_template("investigation/index.html", recent=list_recent(20))


# ── IP Lookup ─────────────────────────────────────────────────────────────────

@investigation_bp.route("/ip", methods=["GET", "POST"])
@login_required
def ip():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        ip_addr = request.form.get("query", "").strip()
        case_id = request.form.get("case_id") or None
        if case_id:
            case_id = int(case_id)
        if not ip_addr:
            flash("IP address is required.", "error")
            return render_template("investigation/ip.html", cases=cases, result=None)

        geo = ip_client.fetch_ip(ip_addr)
        vt = virustotal_client.fetch_virustotal(ip_addr)
        shodan = shodan_client.fetch_shodan(ip_addr)
        result = {"geo": geo, "virustotal": vt, "shodan": shodan}

        create_investigation(kind="ip", query=ip_addr, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"IP lookup complete for {ip_addr}.", "success")

    return render_template("investigation/ip.html", cases=cases, result=result)


# ── Domain WHOIS ──────────────────────────────────────────────────────────────

@investigation_bp.route("/domain", methods=["GET", "POST"])
@login_required
def domain():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        domain_name = request.form.get("query", "").strip()
        case_id = request.form.get("case_id") or None
        if case_id:
            case_id = int(case_id)
        if not domain_name:
            flash("Domain is required.", "error")
            return render_template("investigation/domain.html", cases=cases, result=None)

        result = rdap_client.fetch_domain(domain_name)
        if result is None:
            result = {"registrar": "Unknown", "status": "unknown", "ns": [], "created": "", "expires": ""}

        create_investigation(kind="domain", query=domain_name, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"Domain lookup complete for {domain_name}.", "success")

    return render_template("investigation/domain.html", cases=cases, result=result)


# ── Subdomain Scanner ─────────────────────────────────────────────────────────

@investigation_bp.route("/subdomain", methods=["GET", "POST"])
@login_required
def subdomain():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        domain_name = request.form.get("query", "").strip()
        case_id = request.form.get("case_id") or None
        if case_id:
            case_id = int(case_id)
        if not domain_name:
            flash("Domain is required.", "error")
            return render_template("investigation/subdomain.html", cases=cases, result=None)

        from app.services import subdomain_client
        result = subdomain_client.scan_domain(domain_name)

        create_investigation(kind="subdomain", query=domain_name, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"Subdomain scan complete for {domain_name} — {result.get('subdomains_found', 0)} found.", "success")

    return render_template("investigation/subdomain.html", cases=cases, result=result)


# ── Email Analysis (HIBP + Hunter) ────────────────────────────────────────────

@investigation_bp.route("/email", methods=["GET", "POST"])
@login_required
def email():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        email_addr = request.form.get("query", "").strip()
        case_id = request.form.get("case_id") or None
        if case_id:
            case_id = int(case_id)
        if not email_addr:
            flash("Email address is required.", "error")
            return render_template("investigation/email.html", cases=cases, result=None)

        breaches = hibp_client.check_breaches(email_addr)
        verification = hunter_client.verify_email(email_addr)
        result = {"breaches": breaches, "verification": verification}

        create_investigation(kind="email", query=email_addr, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"Email analysis complete for {email_addr}.", "success")

    return render_template("investigation/email.html", cases=cases, result=result)


# ── Email Header Analyser ─────────────────────────────────────────────────────

@investigation_bp.route("/email-header", methods=["GET", "POST"])
@login_required
def email_header():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        raw = request.form.get("headers", "").strip()
        case_id = request.form.get("case_id") or None
        if case_id:
            case_id = int(case_id)
        if not raw:
            flash("Paste email headers to analyse.", "error")
            return render_template("investigation/email_header.html", cases=cases, result=None)

        from app.services.email_header_client import analyse_headers
        result = analyse_headers(raw)

        create_investigation(kind="email_header", query=result.get("from", "unknown"),
                             result_json=json.dumps(result), user_id=current_user.id, case_id=case_id)
        flash("Email header analysis complete.", "success")

    return render_template("investigation/email_header.html", cases=cases, result=result)


# ── Social Username Search ────────────────────────────────────────────────────

@investigation_bp.route("/social", methods=["GET", "POST"])
@login_required
def social():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        username = request.form.get("query", "").strip()
        case_id = request.form.get("case_id") or None
        if case_id:
            case_id = int(case_id)
        if not username:
            flash("Username is required.", "error")
            return render_template("investigation/social.html", cases=cases, result=None)

        result = social_client.search_username(username)

        create_investigation(kind="social", query=username, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"Social search complete for '{username}' — {result.get('found_count', 0)} of {result.get('total_checked', 0)} profiles found.", "success")

    return render_template("investigation/social.html", cases=cases, result=result)


# ── Phone Lookup ──────────────────────────────────────────────────────────────

@investigation_bp.route("/phone", methods=["GET", "POST"])
@login_required
def phone():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        phone_num = request.form.get("query", "").strip()
        case_id = request.form.get("case_id") or None
        if case_id:
            case_id = int(case_id)
        if not phone_num:
            flash("Phone number is required.", "error")
            return render_template("investigation/phone.html", cases=cases, result=None)

        result = numverify_client.validate_phone(phone_num)
        if result is None:
            result = {"error": "NumVerify API not configured or unavailable."}

        create_investigation(kind="phone", query=phone_num, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"Phone lookup complete for {phone_num}.", "success")

    return render_template("investigation/phone.html", cases=cases, result=result)


# ── MAC Vendor Lookup ─────────────────────────────────────────────────────────

@investigation_bp.route("/mac", methods=["GET", "POST"])
@login_required
def mac():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        mac_addr = request.form.get("query", "").strip()
        case_id = request.form.get("case_id") or None
        if case_id:
            case_id = int(case_id)
        if not mac_addr:
            flash("MAC address is required.", "error")
            return render_template("investigation/mac.html", cases=cases, result=None)

        from app.services import mac_client
        result = mac_client.lookup_mac(mac_addr)

        create_investigation(kind="mac", query=mac_addr, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"MAC vendor lookup complete for {mac_addr}.", "success")

    return render_template("investigation/mac.html", cases=cases, result=result)


# ── File & Document Forensics ─────────────────────────────────────────────────

@investigation_bp.route("/file", methods=["GET", "POST"])
@login_required
def file_forensics():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        case_id = request.form.get("case_id") or None
        if case_id:
            case_id = int(case_id)

        uploaded = request.files.get("file")
        if not uploaded or uploaded.filename == "":
            flash("No file selected.", "error")
            return render_template("investigation/file_forensics.html", cases=cases, result=None)

        if not _ext_ok(uploaded.filename, ALLOWED_FILE_EXTENSIONS):
            flash("Unsupported file type.", "error")
            return render_template("investigation/file_forensics.html", cases=cases, result=None)

        filename = secure_filename(uploaded.filename)
        if not filename:
            flash("Invalid filename — rename the file and try again.", "error")
            return render_template("investigation/file_forensics.html", cases=cases, result=None)
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)
        filepath = Path(upload_dir) / filename
        uploaded.save(str(filepath))

        from app.services.file_forensics_client import analyse_file
        result = analyse_file(filepath)

        create_investigation(kind="file_forensics", query=filename, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"File forensics complete for {filename}.", "success")

    return render_template("investigation/file_forensics.html",
                           cases=cases, result=result,
                           allowed_types="Images, Audio, Video, PDF, DOCX, XLSX")


# ── Image Forensics (legacy — kept for bookmarks; redirects to /file) ─────────

@investigation_bp.route("/image", methods=["GET", "POST"])
@login_required
def image():
    if request.method == "GET":
        return redirect(url_for("investigation.file_forensics"))

    cases = _cases_for_select()
    case_id = request.form.get("case_id") or None
    if case_id:
        case_id = int(case_id)

    if "image" not in request.files or request.files["image"].filename == "":
        flash("No image file selected.", "error")
        return redirect(url_for("investigation.file_forensics"))

    file = request.files["image"]
    if not _ext_ok(file.filename, ALLOWED_IMAGE_EXTENSIONS):
        flash("Unsupported file type.", "error")
        return redirect(url_for("investigation.file_forensics"))

    filename = secure_filename(file.filename)
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    filepath = Path(upload_dir) / filename
    file.save(str(filepath))

    result = image_client.analyze_image(filepath)
    create_investigation(kind="image", query=filename, result_json=json.dumps(result),
                         user_id=current_user.id, case_id=case_id)
    flash(f"Image analysis complete for {filename}.", "success")
    return render_template("investigation/image.html", cases=cases, result=result)


# ── Crypto / Blockchain Address Lookup ────────────────────────────────────────

@investigation_bp.route("/crypto", methods=["GET", "POST"])
@login_required
def crypto():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        address = request.form.get("query", "").strip()
        case_id = request.form.get("case_id") or None
        if case_id:
            case_id = int(case_id)
        if not address:
            flash("Wallet address is required.", "error")
            return render_template("investigation/crypto.html", cases=cases, result=None)

        from app.services.crypto_client import lookup_address
        result = lookup_address(address)

        create_investigation(kind="crypto", query=address, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"Crypto lookup complete for {address[:12]}...", "success")

    return render_template("investigation/crypto.html", cases=cases, result=result)


# ── IMEI Lookup ───────────────────────────────────────────────────────────────

@investigation_bp.route("/imei", methods=["GET", "POST"])
@login_required
def imei():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        imei_num = request.form.get("query", "").strip()
        case_id = request.form.get("case_id") or None
        if case_id:
            case_id = int(case_id)
        if not imei_num:
            flash("IMEI number is required.", "error")
            return render_template("investigation/imei.html", cases=cases, result=None)

        result = imei_client.fetch_imei(imei_num)
        if result is None:
            result = {"error": "IMEI Service not configured or unavailable."}

        create_investigation(kind="imei", query=imei_num, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"IMEI lookup complete for {imei_num}.", "success")

    return render_template("investigation/imei.html", cases=cases, result=result)
