import json
import os
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

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _cases_for_select():
    return list_cases()


@investigation_bp.route("/")
@login_required
def index():
    recent = list_recent(20)
    return render_template("investigation/index.html", recent=recent)


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

        create_investigation(
            kind="ip",
            query=ip_addr,
            result_json=json.dumps(result),
            user_id=current_user.id,
            case_id=case_id,
        )
        flash(f"IP lookup complete for {ip_addr}.", "success")

    return render_template("investigation/ip.html", cases=cases, result=result)


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

        create_investigation(
            kind="domain",
            query=domain_name,
            result_json=json.dumps(result),
            user_id=current_user.id,
            case_id=case_id,
        )
        flash(f"Domain lookup complete for {domain_name}.", "success")

    return render_template("investigation/domain.html", cases=cases, result=result)


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

        create_investigation(
            kind="email",
            query=email_addr,
            result_json=json.dumps(result),
            user_id=current_user.id,
            case_id=case_id,
        )
        flash(f"Email analysis complete for {email_addr}.", "success")

    return render_template("investigation/email.html", cases=cases, result=result)


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

        result = social_client.fetch_social(username)

        create_investigation(
            kind="social",
            query=username,
            result_json=json.dumps(result),
            user_id=current_user.id,
            case_id=case_id,
        )
        flash(f"Social search complete for {username}.", "success")

    return render_template("investigation/social.html", cases=cases, result=result)


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

        create_investigation(
            kind="phone",
            query=phone_num,
            result_json=json.dumps(result),
            user_id=current_user.id,
            case_id=case_id,
        )
        flash(f"Phone lookup complete for {phone_num}.", "success")

    return render_template("investigation/phone.html", cases=cases, result=result)


@investigation_bp.route("/image", methods=["GET", "POST"])
@login_required
def image():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        case_id = request.form.get("case_id") or None
        if case_id:
            case_id = int(case_id)

        if "image" not in request.files or request.files["image"].filename == "":
            flash("No image file selected.", "error")
            return render_template("investigation/image.html", cases=cases, result=None)

        file = request.files["image"]
        if not _allowed_file(file.filename):
            flash("Unsupported file type.", "error")
            return render_template("investigation/image.html", cases=cases, result=None)

        filename = secure_filename(file.filename)
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        from pathlib import Path
        result = image_client.analyze_image(Path(filepath))

        create_investigation(
            kind="image",
            query=filename,
            result_json=json.dumps(result),
            user_id=current_user.id,
            case_id=case_id,
        )
        flash(f"Image analysis complete for {filename}.", "success")

    return render_template("investigation/image.html", cases=cases, result=result)


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

        create_investigation(
            kind="imei",
            query=imei_num,
            result_json=json.dumps(result),
            user_id=current_user.id,
            case_id=case_id,
        )
        flash(f"IMEI lookup complete for {imei_num}.", "success")

    return render_template("investigation/imei.html", cases=cases, result=result)
