import json
import os
import uuid
from pathlib import Path

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify, session
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


def _safe_case_id(raw: str | None) -> int | None:
    """Parse case_id from form safely; return None on bad input."""
    if not raw:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def _cases_for_select():
    return list_cases()


@investigation_bp.before_request
def _investigation_before():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return
    # Require at least one case to exist
    cases = _cases_for_select()
    if not cases:
        flash("Please create a case first before running investigations.", "error")
        return redirect(url_for('cases.new'))
    # On POST, a case must be explicitly selected
    if request.method == 'POST':
        cid = _safe_case_id(request.form.get('case_id'))
        if cid:
            session['active_case_id'] = cid
        else:
            flash("You must select a case before running this tool.", "error")
            return redirect(request.url)


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
        case_id = _safe_case_id(request.form.get("case_id"))
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
        case_id = _safe_case_id(request.form.get("case_id"))
        if not domain_name:
            flash("Domain is required.", "error")
            return render_template("investigation/domain.html", cases=cases, result=None)

        result = rdap_client.fetch_domain(domain_name)
        if result is None:
            flash(f"WHOIS lookup failed for '{domain_name}'. The domain may not exist or RDAP is temporarily unavailable.", "error")
            return render_template("investigation/domain.html", cases=cases, result=None)

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
        case_id = _safe_case_id(request.form.get("case_id"))
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
        case_id = _safe_case_id(request.form.get("case_id"))
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
        case_id = _safe_case_id(request.form.get("case_id"))
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
        case_id = _safe_case_id(request.form.get("case_id"))
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
        case_id = _safe_case_id(request.form.get("case_id"))
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
        case_id = _safe_case_id(request.form.get("case_id"))
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
        case_id = _safe_case_id(request.form.get("case_id"))

        uploaded = request.files.get("file")
        if not uploaded or uploaded.filename == "":
            flash("No file selected.", "error")
            return render_template("investigation/file_forensics.html", cases=cases, result=None)

        if not _ext_ok(uploaded.filename, ALLOWED_FILE_EXTENSIONS):
            flash("Unsupported file type.", "error")
            return render_template("investigation/file_forensics.html", cases=cases, result=None)

        original_name = secure_filename(uploaded.filename)
        if not original_name:
            flash("Invalid filename — rename the file and try again.", "error")
            return render_template("investigation/file_forensics.html", cases=cases, result=None)
        ext = os.path.splitext(original_name)[1].lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)
        filepath = Path(upload_dir) / filename
        uploaded.save(str(filepath))

        from app.services.file_forensics_client import analyse_file
        try:
            result = analyse_file(filepath)
        finally:
            try:
                filepath.unlink(missing_ok=True)
            except Exception:
                pass

        create_investigation(kind="file_forensics", query=original_name, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"File forensics complete for {original_name}.", "success")

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
        case_id = _safe_case_id(request.form.get("case_id"))
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
        case_id = _safe_case_id(request.form.get("case_id"))
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


# ── Dark Web Monitor ──────────────────────────────────────────────────────────

@investigation_bp.route("/darkweb", methods=["GET", "POST"])
@login_required
def darkweb():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        case_id = _safe_case_id(request.form.get("case_id"))
        if not query:
            flash("Search term is required.", "error")
            return render_template("investigation/darkweb.html", cases=cases, result=None)

        from app.services import darkweb_client
        result = darkweb_client.search_ahmia(query)

        create_investigation(kind="darkweb", query=query, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"Dark web search complete: {result.get('total', 0)} results found.", "success")

    return render_template("investigation/darkweb.html", cases=cases, result=result)


# ── Network Graph ─────────────────────────────────────────────────────────────

@investigation_bp.route("/graph")
@login_required
def graph():
    return render_template("investigation/graph.html")


@investigation_bp.route("/graph/data")
@login_required
def graph_data():
    """Return JSON graph data: nodes + edges for vis.js."""
    from app.repositories.investigation_repository import list_recent
    from app.repositories.case_repository import list_cases
    invs = list_recent(200)
    cases = list_cases()

    nodes = []
    edges = []

    for case in cases:
        nodes.append({
            "id": f"case-{case.id}",
            "label": case.title[:30],
            "group": "case",
            "title": f"Case: {case.title}\nStatus: {case.status}\nPriority: {case.priority}",
        })

    for inv in invs:
        inv_node_id = f"inv-{inv.id}"
        label = f"{inv.query[:20]}\n({inv.kind.replace('_', ' ')})"
        nodes.append({
            "id": inv_node_id,
            "label": label,
            "group": inv.kind,
            "title": f"Type: {inv.kind}\nQuery: {inv.query}\nDate: {inv.created_at.strftime('%Y-%m-%d') if inv.created_at else ''}",
        })
        if inv.case_id:
            edges.append({"from": f"case-{inv.case_id}", "to": inv_node_id})
        # Expand subdomain results as child nodes
        if inv.kind == "subdomain" and inv.result_json:
            try:
                sd_data = json.loads(inv.result_json)
                for i, sub in enumerate(sd_data.get("subdomains", [])[:50]):
                    hostname = sub.get("hostname", "")
                    if hostname:
                        sub_node_id = f"sub-{inv.id}-{i}"
                        nodes.append({
                            "id": sub_node_id,
                            "label": hostname[:28],
                            "group": "subdomain",
                            "title": f"Subdomain: {hostname}\nIP: {sub.get('ip', 'unresolved')}",
                        })
                        edges.append({"from": inv_node_id, "to": sub_node_id, "color": "#6ee7b7"})
            except Exception:
                pass

    return jsonify({"nodes": nodes, "edges": edges})


# ── Company Registry Search ───────────────────────────────────────────────────

@investigation_bp.route("/company", methods=["GET", "POST"])
@login_required
def company():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        name = request.form.get("query", "").strip()
        case_id = _safe_case_id(request.form.get("case_id"))
        if not name:
            flash("Company name is required.", "error")
            return render_template("investigation/company.html", cases=cases, result=None)

        from app.services import company_client
        from app.repositories.api_config_repository import get_by_service
        uk_cfg = get_by_service("companies_house")
        uk_key = uk_cfg.api_key if uk_cfg and uk_cfg.is_enabled else None
        result = company_client.search_companies(name, uk_api_key=uk_key)

        create_investigation(kind="company", query=name, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        total = sum(len(v.get("found", [])) for v in result.get("results", {}).values())
        flash(f"Company search for '{name}' complete — {total} results across registries.", "success")

    return render_template("investigation/company.html", cases=cases, result=result)


# ── Person / Full Name Search ─────────────────────────────────────────────────

@investigation_bp.route("/person", methods=["GET", "POST"])
@login_required
def person():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        name = request.form.get("query", "").strip()
        case_id = _safe_case_id(request.form.get("case_id"))
        if not name:
            flash("Full name is required.", "error")
            return render_template("investigation/person.html", cases=cases, result=None)

        from app.services.person_client import search_person
        result = search_person(name)

        create_investigation(kind="person", query=name, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        flash(f"Person investigation links generated for '{name}'.", "success")

    return render_template("investigation/person.html", cases=cases, result=result)


# ── Vehicle / VIN Lookup ──────────────────────────────────────────────────────

@investigation_bp.route("/vehicle", methods=["GET", "POST"])
@login_required
def vehicle():
    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        vin = request.form.get("query", "").strip()
        case_id = _safe_case_id(request.form.get("case_id"))
        if not vin:
            flash("VIN is required.", "error")
            return render_template("investigation/vehicle.html", cases=cases, result=None)

        from app.services.vehicle_client import decode_vin
        result = decode_vin(vin)

        create_investigation(kind="vehicle", query=vin, result_json=json.dumps(result),
                             user_id=current_user.id, case_id=case_id)
        if result.get("error"):
            flash(f"VIN decode error: {result['error']}", "error")
        else:
            s = result.get("summary", {})
            flash(f"VIN decoded: {s.get('year','')} {s.get('make','')} {s.get('model','')}.", "success")

    return render_template("investigation/vehicle.html", cases=cases, result=result)


# ── Location Map ──────────────────────────────────────────────────────────────

@investigation_bp.route("/map")
@login_required
def location_map():
    return render_template("investigation/map.html")


@investigation_bp.route("/map/data")
@login_required
def map_data():
    """Return JSON markers extracted from geo-tagged investigations."""
    from app.repositories.investigation_repository import list_recent
    invs = list_recent(500)
    markers = []

    for inv in invs:
        if not inv.result_json:
            continue
        try:
            data = json.loads(inv.result_json)
        except Exception:
            continue

        lat = lon = label = info = None

        if inv.kind == "ip":
            geo = data.get("geo") or {}
            lat = geo.get("lat")
            lon = geo.get("lon")
            if lat and lon:
                label = f"IP: {inv.query}"
                info = f"{geo.get('city', '')}, {geo.get('country', '')}<br>ISP: {geo.get('isp', '')}"

        elif inv.kind == "file_forensics":
            coords = (data.get("metadata") or {}).get("GPS_Coordinates") or \
                     (data.get("metadata") or {}).get("GPS_Coordinates")
            if not coords:
                coords = data.get("metadata", {}).get("GPS_Coordinates")
            if coords and isinstance(coords, str) and "," in coords:
                try:
                    parts = coords.split(",")
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    label = f"Image GPS: {inv.query}"
                    info = (data.get("location") or
                            (data.get("metadata") or {}).get("GPS_Location") or
                            coords)
                except (ValueError, IndexError):
                    pass

        if lat is not None and lon is not None:
            markers.append({
                "lat": lat,
                "lon": lon,
                "label": label,
                "info": info or "",
                "kind": inv.kind,
                "date": inv.created_at.strftime("%Y-%m-%d") if inv.created_at else "",
            })

    return jsonify({"markers": markers})


# ── Plugins ───────────────────────────────────────────────────────────────────

@investigation_bp.route("/plugins")
@login_required
def plugins():
    from app.plugins import get_all
    all_plugins = get_all()
    return render_template("investigation/plugins.html", plugins=all_plugins)


@investigation_bp.route("/plugins/<plugin_name>", methods=["GET", "POST"])
@login_required
def plugin_run(plugin_name):
    from app.plugins import get_plugin
    plugin = get_plugin(plugin_name)
    if not plugin:
        flash(f"Plugin '{plugin_name}' not found.", "error")
        return redirect(url_for("investigation.plugins"))

    cases = _cases_for_select()
    result = None
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        case_id = _safe_case_id(request.form.get("case_id"))
        if not query:
            flash("Query is required.", "error")
        else:
            try:
                result = plugin.run(query)
            except Exception as exc:
                result = {"error": str(exc)}
            create_investigation(kind=f"plugin_{plugin.name}", query=query,
                                 result_json=json.dumps(result),
                                 user_id=current_user.id, case_id=case_id)
            flash(f"Plugin '{plugin.label}' completed.", "success")

    return render_template("investigation/plugin_run.html",
                           plugin=plugin, cases=cases, result=result)
