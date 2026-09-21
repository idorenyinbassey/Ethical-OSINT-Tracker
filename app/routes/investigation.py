import json
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify, session, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.repositories.investigation_repository import create_investigation, list_recent, find_or_update_recent, update_tags, list_by_case_and_kind
from app.repositories.case_repository import list_cases, get_case
from app.utils.authz import can_access_case
from app.services import (
    ip_client, rdap_client, hibp_client, hunter_client,
    social_client, image_client, imei_client,
    virustotal_client, shodan_client,
)

investigation_bp = Blueprint("investigation", __name__, url_prefix="/investigate")

# Social usernames may only contain letters, digits, and . _ - (1–50 chars).
# This blocks format-string/path-traversal payloads (e.g. "{username.__class__}"
# or "../admin") from ever reaching the site URL templates in social_client.
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,50}$")

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
    return list_cases(owner_user_id=current_user.id)


def _resolve_case_context() -> int | None:
    """Read case_id from the POST form (a search being run) or the GET
    query string (the "Link to Case" dropdown reloading the page to show
    that case's history for this tool), and access-check it if present.

    Every tool route calls this once at the top, before its own POST
    handling — closes a latent gap where case_id was previously only
    ever read from POST with no ownership/team-access check at all, so a
    crafted request could write (and, now that GET reads case_id too,
    read) another user's case data.
    """
    if request.method == "POST":
        case_id = _safe_case_id(request.form.get("case_id"))
    else:
        case_id = request.args.get("case_id", type=int)
    if case_id is not None:
        case = get_case(case_id)
        if not case or not can_access_case(case, current_user, action="read"):
            abort(403)
    return case_id


def _prefill_query() -> str:
    """A GET-only ?query= param, used solely to prefill a tool's own
    input field — e.g. an "Investigate with Email Analysis ->" pivot
    link on an extracted value elsewhere lands here with that value
    ready to run, rather than requiring it to be retyped. Never read on
    POST, where request.form['query'] is the real submitted value."""
    if request.method == "GET":
        return request.args.get("query", "")
    return ""


@investigation_bp.before_request
def _investigation_before():
    from flask_login import current_user
    if not current_user.is_authenticated:
        return
    # JSON data endpoints are consumed by fetch() — skip case enforcement
    # so they return proper JSON instead of an HTML redirect.
    if request.endpoint in ("investigation.graph_data", "investigation.map_data",
                            "investigation.watchlist", "investigation.watchlist_add",
                            "investigation.watchlist_remove", "investigation.watchlist_rescan",
                            "investigation.watchlist_dismiss_alert",
                            "investigation.tag_investigation",
                            "investigation.scan_progress_status"):
        return
    # Require at least one case to exist (owned, or shared via a team —
    # a team-only member must not be locked out of every investigation
    # page just because they don't own any case themselves).
    from app.repositories.case_repository import list_cases_for_user
    cases = list_cases_for_user(current_user.id)
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
    return render_template("investigation/index.html", recent=list_recent(20, user_id=current_user.id))


# ── IP Lookup ─────────────────────────────────────────────────────────────────

@investigation_bp.route("/ip", methods=["GET", "POST"])
@login_required
def ip():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        ip_addr = request.form.get("query", "").strip()
        if not ip_addr:
            flash("IP address is required.", "error")
        else:
            geo = ip_client.fetch_ip(ip_addr)
            vt = virustotal_client.fetch_virustotal(ip_addr)
            shodan = shodan_client.fetch_shodan(ip_addr)
            result = {"geo": geo, "virustotal": vt, "shodan": shodan}

            conf = "CONFIRMED" if result.get("geo") and not result["geo"].get("error") else "UNVERIFIED"
            inv = find_or_update_recent(kind="ip", query=ip_addr, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            flash(f"IP lookup complete for {ip_addr}.", "success")

    history = list_by_case_and_kind(case_id, "ip", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/ip.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id, prefill_query=_prefill_query())


# ── Domain WHOIS ──────────────────────────────────────────────────────────────

@investigation_bp.route("/domain", methods=["GET", "POST"])
@login_required
def domain():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        domain_name = request.form.get("query", "").strip()
        if not domain_name:
            flash("Domain is required.", "error")
        else:
            result = rdap_client.fetch_domain(domain_name)
            if result is None:
                flash(f"WHOIS lookup failed for '{domain_name}'. The domain may not exist or RDAP is temporarily unavailable.", "error")
            else:
                conf = "CONFIRMED" if result and not result.get("error") else "UNVERIFIED"
                inv = find_or_update_recent(kind="domain", query=domain_name, result_json=json.dumps(result),
                                      user_id=current_user.id, case_id=case_id, confidence=conf)
                flash(f"Domain lookup complete for {domain_name}.", "success")

    history = list_by_case_and_kind(case_id, "domain", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/domain.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id, prefill_query=_prefill_query())


# ── Subdomain Scanner ─────────────────────────────────────────────────────────

@investigation_bp.route("/subdomain", methods=["GET", "POST"])
@login_required
def subdomain():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        domain_name = request.form.get("query", "").strip()
        if not domain_name:
            flash("Domain is required.", "error")
        else:
            from app.services import subdomain_client
            result = subdomain_client.scan_domain(domain_name)

            conf = "CONFIRMED" if result.get("subdomains_found", 0) > 0 else "UNVERIFIED"
            inv = find_or_update_recent(kind="subdomain", query=domain_name, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            msg = f"Subdomain scan complete for {domain_name} — {result.get('subdomains_found', 0)} found."
            takeover_count = result.get("takeover_count", 0)
            if takeover_count > 0:
                msg += f" {takeover_count} possible takeover(s) detected — verify manually."
            flash(msg, "success")

    history = list_by_case_and_kind(case_id, "subdomain", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/subdomain.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id)


# ── Domain Typosquat Monitor ───────────────────────────────────────────────────

@investigation_bp.route("/typosquat", methods=["GET", "POST"])
@login_required
def typosquat():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        domain_name = request.form.get("query", "").strip()
        if not domain_name:
            flash("Domain is required.", "error")
        else:
            from app.services import typosquat_client
            result = typosquat_client.scan_typosquats(domain_name)

            conf = "CONFIRMED" if result.get("registered_count", 0) > 0 else "UNVERIFIED"
            inv = find_or_update_recent(kind="typosquat", query=domain_name, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            flash(f"Typosquat scan complete for {domain_name} — "
                  f"{result.get('registered_count', 0)} registered lookalike(s) found.", "success")

    history = list_by_case_and_kind(case_id, "typosquat", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/typosquat.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id)


# ── Email Analysis (HIBP + Hunter) ────────────────────────────────────────────

@investigation_bp.route("/email", methods=["GET", "POST"])
@login_required
def email():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        email_addr = request.form.get("query", "").strip()
        if not email_addr:
            flash("Email address is required.", "error")
        else:
            breaches = hibp_client.check_breaches(email_addr)
            verification = hunter_client.verify_email(email_addr)
            result = {"breaches": breaches, "verification": verification}

            breaches = result.get("breaches")
            conf = "CONFIRMED" if breaches and breaches != "No breaches found" else "UNVERIFIED"
            inv = find_or_update_recent(kind="email", query=email_addr, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            flash(f"Email analysis complete for {email_addr}.", "success")

    history = list_by_case_and_kind(case_id, "email", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/email.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id, prefill_query=_prefill_query())


# ── Email Header Analyser ─────────────────────────────────────────────────────

@investigation_bp.route("/email-header", methods=["GET", "POST"])
@login_required
def email_header():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        raw = request.form.get("headers", "").strip()
        if not raw:
            flash("Paste email headers to analyse.", "error")
        else:
            from app.services.email_header_client import analyse_headers
            result = analyse_headers(raw)

            inv = find_or_update_recent(kind="email_header", query=result.get("from", "unknown"),
                                  result_json=json.dumps(result), user_id=current_user.id,
                                  case_id=case_id, confidence="CONFIRMED")
            flash("Email header analysis complete.", "success")

    history = list_by_case_and_kind(case_id, "email_header", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/email_header.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id)


# ── Scan progress polling (Social Search, Company Registry) ─────────────────
# A tool page's own POST keeps running its scan synchronously and unchanged;
# this is a purely additive side channel the page polls concurrently (via a
# fetch()-based submit, not a native form post) to show "N of M checked"
# instead of a blank wait. See app.utils.scan_progress.

@investigation_bp.route("/scan-progress/<token>")
@login_required
def scan_progress_status(token):
    from app.utils import scan_progress
    return jsonify(scan_progress.get_progress(token))


# ── Social Username Search ────────────────────────────────────────────────────

@investigation_bp.route("/social", methods=["GET", "POST"])
@login_required
def social():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    status = 200
    if request.method == "POST":
        username = request.form.get("query", "").strip()
        if not username:
            flash("Username is required.", "error")
        elif not USERNAME_PATTERN.match(username):
            flash(
                "Invalid username — use only letters, numbers, dots, "
                "underscores, and dashes (max 50 characters).",
                "error",
            )
            status = 400
        else:
            from app.utils import scan_progress
            progress_cb = scan_progress.make_callback(request.form.get("progress_token"))
            result = social_client.search_username(username, progress_cb=progress_cb)

            confirmed = result.get("confirmed_count", 0)
            found = result.get("found_count", 0)
            conf = "CONFIRMED" if confirmed > 0 else ("POSSIBLE" if found > 0 else "UNVERIFIED")
            inv = find_or_update_recent(kind="social", query=username, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            flash(f"Social search complete for '{username}' — {result.get('found_count', 0)} of {result.get('total_checked', 0)} profiles found.", "success")

    history = list_by_case_and_kind(case_id, "social", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/social.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id), status


# ── Phone Lookup ──────────────────────────────────────────────────────────────

@investigation_bp.route("/phone", methods=["GET", "POST"])
@login_required
def phone():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        phone_num = request.form.get("query", "").strip()
        if not phone_num:
            flash("Phone number is required.", "error")
        else:
            from app.services import phone_client
            result = phone_client.lookup_phone(phone_num)

            conf = "CONFIRMED" if result and not result.get("error") and result.get("valid") else "UNVERIFIED"
            inv = find_or_update_recent(kind="phone", query=phone_num, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            flash(f"Phone lookup complete for {phone_num}.", "success")

    history = list_by_case_and_kind(case_id, "phone", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/phone.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id, prefill_query=_prefill_query())


# ── MAC Vendor Lookup ─────────────────────────────────────────────────────────

@investigation_bp.route("/mac", methods=["GET", "POST"])
@login_required
def mac():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        mac_addr = request.form.get("query", "").strip()
        if not mac_addr:
            flash("MAC address is required.", "error")
        else:
            from app.services import mac_client
            result = mac_client.lookup_mac(mac_addr)

            conf = "CONFIRMED" if result and not result.get("error") else "UNVERIFIED"
            inv = find_or_update_recent(kind="mac", query=mac_addr, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            flash(f"MAC vendor lookup complete for {mac_addr}.", "success")

    history = list_by_case_and_kind(case_id, "mac", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/mac.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id)


# ── File & Document Forensics ─────────────────────────────────────────────────

@investigation_bp.route("/file", methods=["GET", "POST"])
@login_required
def file_forensics():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        uploaded = request.files.get("file")
        original_name = secure_filename(uploaded.filename) if uploaded and uploaded.filename else ""
        if not uploaded or uploaded.filename == "":
            flash("No file selected.", "error")
        elif not _ext_ok(uploaded.filename, ALLOWED_FILE_EXTENSIONS):
            flash("Unsupported file type.", "error")
        elif not original_name:
            flash("Invalid filename — rename the file and try again.", "error")
        else:
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

            conf = "CONFIRMED" if result and not result.get("error") else "UNVERIFIED"
            inv = find_or_update_recent(kind="file_forensics", query=original_name, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            flash(f"File forensics complete for {original_name}.", "success")

    history = list_by_case_and_kind(case_id, "file_forensics", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/file_forensics.html",
                           cases=cases, result=result, history=history, selected_case_id=case_id,
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

    original_filename = secure_filename(file.filename)
    if not original_filename:
        flash("Invalid filename — rename the file and try again.", "error")
        return redirect(url_for("investigation.file_forensics"))

    # Generate UUID-based filename to avoid collisions
    ext = os.path.splitext(original_filename)[1].lower()
    uuid_filename = f"{uuid.uuid4().hex}{ext}"

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    filepath = Path(upload_dir) / uuid_filename

    try:
        file.save(str(filepath))
        result = image_client.analyze_image(filepath)
        # Store original filename (not UUID) in investigation record for user display
        find_or_update_recent(kind="image", query=original_filename, result_json=json.dumps(result),
                              user_id=current_user.id, case_id=case_id, confidence="CONFIRMED")
        flash(f"Image analysis complete for {original_filename}.", "success")
        return render_template("investigation/image.html", cases=cases, result=result)
    finally:
        # Always cleanup uploaded file after analysis completes
        try:
            filepath.unlink(missing_ok=True)
        except Exception:
            pass  # Ignore cleanup errors


# ── Crypto / Blockchain Address Lookup ────────────────────────────────────────

@investigation_bp.route("/crypto", methods=["GET", "POST"])
@login_required
def crypto():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        address = request.form.get("query", "").strip()
        if not address:
            flash("Wallet address is required.", "error")
        else:
            from app.services.crypto_client import lookup_address
            result = lookup_address(address)

            conf = "CONFIRMED" if result and not result.get("error") else "UNVERIFIED"
            inv = find_or_update_recent(kind="crypto", query=address, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            flash(f"Crypto lookup complete for {address[:12]}...", "success")

    history = list_by_case_and_kind(case_id, "crypto", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/crypto.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id)


# ── IMEI Lookup ───────────────────────────────────────────────────────────────

@investigation_bp.route("/imei", methods=["GET", "POST"])
@login_required
def imei():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        imei_num = request.form.get("query", "").strip()
        if not imei_num:
            flash("IMEI number is required.", "error")
        else:
            result = imei_client.fetch_imei(imei_num)

            conf = "CONFIRMED" if result and not result.get("error") and not result.get("not_configured") and not result.get("unverified") else "UNVERIFIED"
            inv = find_or_update_recent(kind="imei", query=imei_num, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            flash(f"IMEI lookup complete for {imei_num}.", "success")

    history = list_by_case_and_kind(case_id, "imei", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/imei.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id)


# ── Dark Web Monitor ──────────────────────────────────────────────────────────

@investigation_bp.route("/darkweb", methods=["GET", "POST"])
@login_required
def darkweb():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        query_str = request.form.get("query", "").strip()
        if not query_str:
            flash("Search term is required.", "error")
        else:
            from app.services import darkweb_client
            result = darkweb_client.search_ahmia(query_str)

            conf = "CONFIRMED" if result.get("total", 0) > 0 else "UNVERIFIED"
            inv = find_or_update_recent(kind="darkweb", query=query_str, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            flash(f"Dark web search complete: {result.get('total', 0)} results found.", "success")

    history = list_by_case_and_kind(case_id, "darkweb", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/darkweb.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id)


# ── Network Graph ─────────────────────────────────────────────────────────────

@investigation_bp.route("/graph")
@login_required
def graph():
    from app.repositories.case_repository import list_cases_for_user
    return render_template("investigation/graph.html", cases=list_cases_for_user(current_user.id))


def _register_entity(entity_map: dict, node_id: str, etype: str, val) -> None:
    """Register a (etype, value) pair as sourced from node_id — shared by
    _extract_entities() (per-investigation extraction) and graph_data()
    (used directly for non-Investigation sources, e.g. Link Tracker hits),
    so both feed the same entity-hub linking loop in graph_data()."""
    val = str(val).strip().lower()
    if val and val != "n/a" and len(val) > 2:
        key = (etype, val)
        entity_map.setdefault(key, [])
        if node_id not in entity_map[key]:
            entity_map[key].append(node_id)


def _domain_of(url_or_host: str) -> str:
    """Best-effort domain/netloc extraction from a URL or bare hostname."""
    if "://" not in url_or_host:
        url_or_host = f"//{url_or_host}"
    return urlparse(url_or_host, scheme="http").netloc


def _extract_entities(inv, data: dict, inv_node_id: str, entity_map: dict) -> None:
    """Extract entity values from result data and register them in the hub map."""
    def _reg(etype, val):
        _register_entity(entity_map, inv_node_id, etype, val)

    kind = inv.kind
    if kind == "ip":
        geo = data.get("geo") or data
        ip_val = data.get("ip") or data.get("query") or inv.query
        _reg("ip", ip_val)
        org = geo.get("org") or geo.get("as") or ""
        if org:
            _reg("org", org[:40])
        # Shodan's own org/hostnames — a separate source from geo's ASN
        # org, so an infrastructure org Shodan identifies can hub-link with
        # a Company Registry search on the same name, and a Shodan hostname
        # can hub-link with a plain domain investigation on the same host.
        shodan = data.get("shodan") or {}
        shodan_org = shodan.get("organization") or ""
        if shodan_org and shodan_org != "Unknown":
            _reg("org", shodan_org[:40])
        for hostname in shodan.get("hostnames", []):
            _reg("domain", hostname)
    elif kind == "domain":
        domain = data.get("domain") or data.get("ldhName") or inv.query
        _reg("domain", domain)
        reg_email = data.get("registrantEmail") or (
            data.get("registrant", {}).get("email") if isinstance(data.get("registrant"), dict) else None)
        if reg_email:
            _reg("email", reg_email)
    elif kind == "email":
        email = data.get("email") or data.get("address") or inv.query
        _reg("email", email)
    elif kind == "social":
        username = data.get("username") or inv.query
        _reg("username", username)
        # Emails/rel="me" cross-links scraped from confirmed profile pages
        # (app.services.social_client._extract_contact_info) — same entity
        # kinds as every other tool, so they hub with any other
        # investigation that references the same address/domain.
        for site_result in data.get("results", []):
            for email in site_result.get("emails", []):
                _reg("email", email)
            for domain in site_result.get("linked_domains", []):
                _reg("domain", domain)
    elif kind == "crypto":
        addr = data.get("address") or inv.query
        _reg("crypto", addr)
        # Sender/recipient addresses pulled from the same transaction data
        # already fetched by app.services.crypto_client — lets two wallets
        # that have transacted with each other show up linked.
        for cp in data.get("counterparties", []):
            _reg("crypto", cp)
    elif kind == "phone":
        phone = data.get("phone_number") or inv.query
        _reg("phone", phone)
    elif kind == "email_header":
        orig_ip = data.get("received_from") or data.get("x_originating_ip") or data.get("originating_ip")
        if orig_ip:
            _reg("ip", str(orig_ip))
        sender = data.get("from") or data.get("From") or ""
        if "@" in sender:
            _reg("email", sender)
    elif kind == "subdomain":
        domain = data.get("domain") or inv.query
        _reg("domain", domain)
        # Each subdomain's already-resolved IP (app.services.subdomain_client's
        # socket.gethostbyname() step) — lets a subdomain scan hub-link with
        # an unrelated IP Lookup investigation that hit the same address.
        for sub in data.get("subdomains", []):
            ip = sub.get("ip")
            if ip:
                _reg("ip", ip)
    elif kind == "typosquat":
        domain = data.get("domain") or inv.query
        _reg("domain", domain)
    elif kind == "paste_leak":
        from app.utils.validators import classify_query_kind
        query = data.get("query") or inv.query
        _reg(classify_query_kind(query), query)
    elif kind == "darkweb":
        # Each hit's .onion host, parsed out of its URL — AHMIA's result
        # items carry no separate domain field (app.services.darkweb_client).
        for site_result in data.get("results", []):
            onion_host = _domain_of(site_result.get("url", ""))
            if onion_host:
                _reg("domain", onion_host)
    elif kind == "company":
        # The searched company name itself, so it can hub-link with a
        # Shodan-discovered org or another registry search on the same name.
        query = data.get("query") or inv.query
        if query:
            _reg("org", query[:40])
        # DuckDuckGo's Instant Answer "Infobox" is the only company-registry
        # source with genuine contact fields — none of the statutory
        # registries (SEC EDGAR, UK Companies House, CAC Nigeria, Corporations
        # Canada, Cyprus DRCOR, Singapore, Estonia, Ireland, Brazil,
        # Australia, New Zealand) reliably expose officer emails/phones.
        ddg_info = ((data.get("results") or {}).get("duckduckgo") or {}).get("info", {})
        if ddg_info.get("email"):
            _reg("email", ddg_info["email"])
        if ddg_info.get("website"):
            domain = _domain_of(ddg_info["website"])
            if domain:
                _reg("domain", domain)
        if ddg_info.get("phone"):
            _reg("phone", ddg_info["phone"])
        # Every statutory registry's hits share a common shape when
        # present: a "found" list of dicts. Register each hit's
        # registration-number-equivalent field and email (when present)
        # as entities, so e.g. a CAC RC number or a registry-listed email
        # can hub-link with another investigation that references it —
        # covers Nigeria + all newly-added registries with no per-country
        # branch (only UK/Canada/Nigeria/Australia/New Zealand carry a
        # number field today; Singapore/Estonia/Ireland/Brazil are
        # currently manual-referral-only with no structured hits).
        for reg in (data.get("results") or {}).values():
            if not isinstance(reg, dict):
                continue
            for hit in reg.get("found") or []:
                if not isinstance(hit, dict):
                    continue
                number = (hit.get("rc_number") or hit.get("number")
                          or hit.get("abn") or hit.get("nzbn"))
                if number:
                    _reg("company_number", number)
                if hit.get("email"):
                    _reg("email", hit["email"])


@investigation_bp.route("/graph/data")
@login_required
def graph_data():
    """Return JSON graph data: nodes + edges for vis.js.

    With one ?case_id=<id>, scopes to just that case (any team member's
    investigations, per can_access_case) — the default view a user reaches
    from a case's own page, and what the report snapshot capture uses.

    With multiple ?case_id=<id>&case_id=<id2>..., scopes to the UNION of
    exactly those cases — an investigator's deliberate, explicit multi-case
    comparison, not a silent account-wide default. Each case's own bubble
    node + case_inv edges (built below) keep every case's investigations
    visually anchored to their case, so comparing never blends them.

    With no case_id at all, scopes to the current user's own ad-hoc
    (case_id IS NULL) investigations and tracking links only — never to
    every case the user owns. There is no way to see more than one case's
    data at once without explicitly listing each case_id: that's what
    keeps this from becoming the account-wide, cross-case-bleeding
    default the single/no-arg forms used to silently fall back to.
    """
    from app.repositories.investigation_repository import list_by_case, list_all
    from app.repositories.case_repository import get_case
    from app.repositories.tracking_repository import list_links_by_case, list_links, list_hits
    from app.utils.authz import can_access_case

    # Order-preserving de-dup: a repeated ?case_id=1&case_id=1 must not
    # double every node/edge for that case.
    requested_case_ids = list(dict.fromkeys(
        cid for cid in request.args.getlist("case_id", type=int) if cid is not None
    ))

    cases = []
    invs = []
    tracking_links = []
    if requested_case_ids:
        for cid in requested_case_ids:
            target_case = get_case(cid)
            if not target_case or not can_access_case(target_case, current_user, action="read"):
                abort(403)
            cases.append(target_case)
            invs.extend(list_by_case(cid))
            # Same read-access check above already gates this — any team
            # member's tracking links on this case are visible here exactly
            # like their investigations are, not just the current user's own.
            tracking_links.extend(list_links_by_case(cid))
    else:
        invs = [i for i in list_all(user_id=current_user.id) if i.case_id is None]
        tracking_links = [l for l in list_links(user_id=current_user.id) if l.case_id is None]

    comparing_multiple = len(cases) > 1
    case_title_lookup = {c.id: c.title for c in cases}

    nodes = []
    edges = []

    case_ids = {c.id for c in cases}

    for case in cases:
        nodes.append({
            "id": f"case-{case.id}",
            "label": case.title[:30],
            "group": "case",
            "title": f"Case: {case.title}\nStatus: {case.status}\nPriority: {case.priority}",
        })

    # Collect (query, kind) pairs per case for case↔case shared-data edges.
    # Including kind prevents spurious edges when two different tools happen
    # to share the same query string (e.g. "john" as username vs. IP query).
    case_queries: dict = {}
    # entity_inv_map: {(etype, evalue) -> [inv_node_id, ...]} for hub detection
    entity_inv_map: dict = {}

    for inv in invs:
        inv_node_id = f"inv-{inv.id}"
        query_str = inv.query or ""
        label = f"{query_str[:20]}\n({inv.kind.replace('_', ' ')})"
        node_title = f"Type: {inv.kind}\nQuery: {query_str}\nDate: {inv.created_at.strftime('%Y-%m-%d') if inv.created_at else ''}"
        if comparing_multiple and inv.case_id in case_title_lookup:
            node_title += f"\nCase: {case_title_lookup[inv.case_id]}"
        nodes.append({
            "id": inv_node_id,
            "label": label,
            "group": inv.kind,
            "title": node_title,
        })
        if inv.case_id and inv.case_id in case_ids:
            edges.append({
                "from": f"case-{inv.case_id}",
                "to": inv_node_id,
                "edge_type": "case_inv",
            })
            q = query_str.strip().lower()
            if q:
                case_queries.setdefault(inv.case_id, set()).add((q, inv.kind))

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
                        edges.append({
                            "from": inv_node_id,
                            "to": sub_node_id,
                            "edge_type": "subdomain",
                        })
            except Exception:
                pass

        # Expand typosquat results as child nodes (registered lookalikes only —
        # the other ~99 checked-but-unregistered permutations aren't graphed)
        if inv.kind == "typosquat" and inv.result_json:
            try:
                ts_data = json.loads(inv.result_json)
                for i, hit in enumerate(ts_data.get("registered", [])[:50]):
                    hit_domain = hit.get("domain", "")
                    if hit_domain:
                        hit_node_id = f"typosquat-{inv.id}-{i}"
                        nodes.append({
                            "id": hit_node_id,
                            "label": hit_domain[:28],
                            "group": "typosquat_hit",
                            "title": f"Registered lookalike: {hit_domain}\nIP: {hit.get('ip', 'unknown')}\nRegistrar: {hit.get('registrar') or 'unknown'}",
                        })
                        edges.append({
                            "from": inv_node_id,
                            "to": hit_node_id,
                            "edge_type": "typosquat",
                        })
            except Exception:
                pass

        # Extract entity values for hub detection
        if inv.result_json:
            try:
                d = json.loads(inv.result_json)
                _extract_entities(inv, d, inv_node_id, entity_inv_map)
            except Exception:
                pass

    # Link Tracker hits — a separate data model from Investigation (see
    # app/models/tracking_link.py / tracking_hit.py), so it's folded in here
    # rather than through _extract_entities(). Each hit's captured IP is
    # registered into the same entity_inv_map used above, so a tracked
    # visitor's IP can hub-link with an unrelated IP Lookup investigation on
    # that same address — exactly like any Investigation-sourced entity.
    for link in tracking_links:
        link_node_id = f"track-link-{link.id}"
        link_title = f"Tracking link: {link.label}\nDecoy: {link.decoy_mode}"
        hit_case_suffix = ""
        if comparing_multiple and link.case_id in case_title_lookup:
            case_label = case_title_lookup[link.case_id]
            link_title += f"\nCase: {case_label}"
            hit_case_suffix = f"\nCase: {case_label}"
        nodes.append({
            "id": link_node_id,
            "label": link.label[:28] or "(tracking link)",
            "group": "tracking_link",
            "title": link_title,
        })
        # Anchor the link to its case bubble exactly like investigations
        # are (case_inv edges above) — without this, tracking links from
        # different cases in a multi-case comparison are visually
        # indistinguishable from each other.
        if link.case_id and link.case_id in case_ids:
            edges.append({
                "from": f"case-{link.case_id}",
                "to": link_node_id,
                "edge_type": "case_inv",
            })
        for hit in list_hits(link.id):
            if not hit.ip:
                continue
            hit_node_id = f"track-hit-{hit.id}"
            nodes.append({
                "id": hit_node_id,
                "label": hit.ip,
                "group": "tracking_hit",
                "title": f"Tracked hit ({hit.hit_type})\nIP: {hit.ip}\n"
                         f"Location: {hit.city or '?'}, {hit.country or '?'}{hit_case_suffix}",
            })
            edges.append({
                "from": link_node_id,
                "to": hit_node_id,
                "edge_type": "tracking_hit",
            })
            _register_entity(entity_inv_map, hit_node_id, "ip", hit.ip)

    # Build entity hub nodes for entities shared across 2+ investigations
    for entity_key, inv_ids in entity_inv_map.items():
        if len(inv_ids) < 2:
            continue
        etype, evalue = entity_key
        entity_node_id = f"entity-{etype}-{evalue}"
        nodes.append({
            "id": entity_node_id,
            "label": evalue[:24],
            "group": f"entity_{etype}",
            "title": f"Shared {etype}: {evalue}\nLinked to {len(inv_ids)} investigations",
            "is_entity": True,
            # Full, untruncated value — "label" above is cut to 24 chars for
            # display, but a click-to-pivot link (graph.html) needs the real
            # value to prefill a follow-up tool's query with.
            "value": evalue,
        })
        for inv_node_id in inv_ids:
            edges.append({
                "from": inv_node_id,
                "to": entity_node_id,
                "edge_type": "entity",
                "title": f"Shares {etype}: {evalue}",
            })

    # Case↔case edges for shared (query, kind) pairs
    cid_list = list(case_queries.keys())
    for i, cid_a in enumerate(cid_list):
        for cid_b in cid_list[i + 1:]:
            shared = case_queries[cid_a] & case_queries[cid_b]
            if shared:
                shared_preview = ", ".join(q for q, _ in list(shared)[:3])
                edges.append({
                    "from": f"case-{cid_a}",
                    "to": f"case-{cid_b}",
                    "edge_type": "case_case",
                    "title": f"Shared data: {shared_preview}",
                })

    return jsonify({"nodes": nodes, "edges": edges})


# ── Company Registry Search ───────────────────────────────────────────────────

@investigation_bp.route("/company", methods=["GET", "POST"])
@login_required
def company():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        name = request.form.get("query", "").strip()
        if not name:
            flash("Company name is required.", "error")
        else:
            from app.services import company_client
            from app.repositories.api_config_repository import get_by_service
            uk_cfg = get_by_service("companies_house")
            uk_key = uk_cfg.api_key if uk_cfg and uk_cfg.is_enabled else None
            au_cfg = get_by_service("abn_lookup")
            au_key = au_cfg.api_key if au_cfg and au_cfg.is_enabled else None
            nz_cfg = get_by_service("nzbn")
            nz_key = nz_cfg.api_key if nz_cfg and nz_cfg.is_enabled else None
            from app.utils import scan_progress
            progress_cb = scan_progress.make_callback(request.form.get("progress_token"))
            result = company_client.search_companies(
                name, uk_api_key=uk_key, au_api_key=au_key, nz_api_key=nz_key,
                progress_cb=progress_cb,
            )

            reg_results = result.get("results", {})
            has_confirmed = any(isinstance(v.get("found"), list) and v["found"] for v in reg_results.values())
            has_manual = any(v.get("manual_url") for v in reg_results.values() if not v.get("found"))
            ddg_found = reg_results.get("duckduckgo", {}).get("found", False)
            if has_confirmed or ddg_found:
                conf = "CONFIRMED"
            elif has_manual:
                conf = "POSSIBLE"
            else:
                conf = "UNVERIFIED"
            inv = find_or_update_recent(kind="company", query=name, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            total = sum(len(v["found"]) for v in reg_results.values() if isinstance(v.get("found"), list))
            flash(f"Company search for '{name}' complete — {total} results across registries.", "success")

    history = list_by_case_and_kind(case_id, "company", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/company.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id)


# ── Person / Full Name Search ─────────────────────────────────────────────────

@investigation_bp.route("/person", methods=["GET", "POST"])
@login_required
def person():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        name = request.form.get("query", "").strip()
        if not name:
            flash("Full name is required.", "error")
        else:
            from app.services.person_client import search_person
            result = search_person(name)

            inv = find_or_update_recent(kind="person", query=name, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence="CONFIRMED")
            flash(f"Person investigation links generated for '{name}'.", "success")

    history = list_by_case_and_kind(case_id, "person", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/person.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id)


# ── Vehicle / VIN Lookup ──────────────────────────────────────────────────────

@investigation_bp.route("/vehicle", methods=["GET", "POST"])
@login_required
def vehicle():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        vin = request.form.get("query", "").strip()
        if not vin:
            flash("VIN is required.", "error")
        else:
            from app.services.vehicle_client import decode_vin
            result = decode_vin(vin)

            conf = "CONFIRMED" if not result.get("error") else "UNVERIFIED"
            inv = find_or_update_recent(kind="vehicle", query=vin, result_json=json.dumps(result),
                                  user_id=current_user.id, case_id=case_id, confidence=conf)
            if result.get("error"):
                flash(f"VIN decode error: {result['error']}", "error")
            else:
                s = result.get("summary", {})
                flash(f"VIN decoded: {s.get('year','')} {s.get('make','')} {s.get('model','')}.", "success")

    history = list_by_case_and_kind(case_id, "vehicle", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/vehicle.html", cases=cases, result=result,
                           history=history, selected_case_id=case_id)


# ── Location Map ──────────────────────────────────────────────────────────────

@investigation_bp.route("/map")
@login_required
def location_map():
    from app.repositories.case_repository import list_cases_for_user
    return render_template("investigation/map.html", cases=list_cases_for_user(current_user.id))


_KIND_LABEL = {
    "ip": "IP Lookup",
    "file_forensics": "File Forensics",
    "domain": "Domain Lookup",
    "subdomain": "Subdomain Scan",
    "social": "Social Search",
    "email": "Email Lookup",
    "email_header": "Email Header",
    "crypto": "Crypto Lookup",
    "mac": "MAC Lookup",
    "imei": "IMEI Lookup",
    "company": "Company Registry",
    "person": "Person Search",
    "vehicle": "Vehicle/VIN",
}


@investigation_bp.route("/map/data")
@login_required
def map_data():
    """Return JSON markers extracted from geo-tagged investigations.

    With one ?case_id=<id>, scopes to that case's investigations (any team
    member's, per can_access_case) instead of the account-wide default —
    the default view reached from a case's own page, and what the case
    report snapshot capture uses.

    With multiple ?case_id=<id>&case_id=<id2>..., scopes to the UNION of
    exactly those cases (an explicit multi-case comparison) — each marker's
    popup already shows its case name, so markers from different cases
    stay distinguishable rather than blending together.

    With no case_id at all, scopes to the current user's own ad-hoc
    (case_id IS NULL) investigations only — never to every case the user
    owns. Seeing more than one case at once requires explicitly listing
    each case_id: that's what keeps this from becoming the account-wide,
    cross-case-bleeding default the single/no-arg forms used to silently
    fall back to.
    """
    from app.repositories.investigation_repository import list_by_case, list_all
    from app.repositories.case_repository import list_cases, get_case
    from app.utils.authz import can_access_case

    # Order-preserving de-dup: a repeated ?case_id=1&case_id=1 must not
    # double every marker for that case.
    case_ids = list(dict.fromkeys(
        cid for cid in request.args.getlist("case_id", type=int) if cid is not None
    ))

    # Build case_id → title lookup (scoped to current user's cases)
    case_lookup = {c.id: c.title for c in list_cases(owner_user_id=current_user.id)}

    if case_ids:
        invs = []
        for cid in case_ids:
            case = get_case(cid)
            if not case or not can_access_case(case, current_user, action="read"):
                abort(403)
            case_lookup.setdefault(case.id, case.title)
            invs.extend(list_by_case(cid))
    else:
        invs = [i for i in list_all(user_id=current_user.id) if i.case_id is None]

    markers = []

    for inv in invs:
        if not inv.result_json:
            continue
        try:
            data = json.loads(inv.result_json)
        except Exception:
            continue

        case_name = case_lookup.get(inv.case_id, "") if inv.case_id else ""
        tool_label = _KIND_LABEL.get(inv.kind, inv.kind.replace("_", " ").title())

        if inv.kind == "ip":
            geo = data.get("geo") or {}
            lat = geo.get("lat")
            lon = geo.get("lon")
            if lat is None or lon is None:
                continue
            city = geo.get("city", "")
            country = geo.get("country", "")
            isp = geo.get("isp", "")
            info = f"{city}, {country}" + (f"<br>ISP: {isp}" if isp else "")
            markers.append({
                "lat": lat, "lon": lon, "label": inv.query, "case_name": case_name,
                "tool": tool_label, "info": info, "kind": inv.kind,
                # IP geolocation is city/region-level at best — never a
                # confirmed physical location.
                "confidence": "approximate",
                "date": inv.created_at.strftime("%Y-%m-%d") if inv.created_at else "",
            })
            continue

        elif inv.kind == "file_forensics":
            meta = data.get("metadata") or {}
            coords = meta.get("GPS_Coordinates")
            if not (coords and isinstance(coords, str) and "," in coords):
                continue
            try:
                parts = coords.split(",")
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
            except (ValueError, IndexError):
                continue
            info = (data.get("location") or meta.get("GPS_Location") or coords)
            markers.append({
                "lat": lat, "lon": lon, "label": inv.query, "case_name": case_name,
                "tool": tool_label, "info": info, "kind": inv.kind,
                # A camera's own embedded GPS reading — the most direct
                # location signal this app ever has.
                "confidence": "exact",
                "date": inv.created_at.strftime("%Y-%m-%d") if inv.created_at else "",
            })
            continue

        elif inv.kind == "company":
            # Any registry's hits carrying a structured, free-text address
            # (UK, Nigeria, and any future registry that returns one) get
            # geocoded via Nominatim (free, no key, cached;
            # app.services.geocode_client) into a "suspected" marker, since
            # it's the registry's stated address, not independently
            # verified. Capped at the first 3 hits per registry so one page
            # load can't trigger an unbounded run of geocoding requests.
            from app.services import geocode_client
            for reg in (data.get("results") or {}).values():
                if not isinstance(reg, dict):
                    continue
                for hit in (reg.get("found") or [])[:3]:
                    if not isinstance(hit, dict):
                        continue
                    address = (hit.get("address") or "").strip()
                    if not address:
                        continue
                    geocoded = geocode_client.geocode(address)
                    if not geocoded:
                        continue
                    markers.append({
                        "lat": geocoded["lat"], "lon": geocoded["lon"],
                        "label": hit.get("name") or inv.query, "case_name": case_name,
                        "tool": tool_label, "info": geocoded["display_name"] or address,
                        "kind": inv.kind, "confidence": "suspected",
                        "date": inv.created_at.strftime("%Y-%m-%d") if inv.created_at else "",
                    })
            continue

    return jsonify({"markers": markers})


# ── Evidence Tag Update ────────────────────────────────────────────────────────

@investigation_bp.route("/tag/<int:inv_id>", methods=["POST"])
@login_required
def tag_investigation(inv_id):
    tags_raw = request.form.get("tags", "")
    allowed = {"key_evidence", "follow_up", "disputed", "verified", "archived"}
    tags = ",".join(t.strip() for t in tags_raw.split(",") if t.strip() in allowed)
    update_tags(inv_id, tags)
    return ("", 204)


# ── Watchlist ──────────────────────────────────────────────────────────────────

@investigation_bp.route("/watchlist")
@login_required
def watchlist():
    from app.repositories.watchlist_repository import list_targets
    from app.repositories.case_repository import list_cases
    targets = list_targets(user_id=current_user.id)
    cases = list_cases(owner_user_id=current_user.id)
    case_map = {c.id: c.title for c in cases}
    return render_template("investigation/watchlist.html", targets=targets, case_map=case_map, cases=cases)


@investigation_bp.route("/watchlist/add", methods=["POST"])
@login_required
def watchlist_add():
    from app.repositories.watchlist_repository import add_target
    query = request.form.get("query", "").strip()
    kind = request.form.get("kind", "ip").strip()
    case_id = _safe_case_id(request.form.get("case_id"))
    notes = request.form.get("notes", "").strip()
    valid_kinds = {"ip", "domain", "email", "social", "crypto", "phone", "darkweb", "typosquat", "paste_leak"}
    if not query or kind not in valid_kinds:
        flash("Query and a valid kind are required.", "error")
        return redirect(url_for("investigation.watchlist"))
    add_target(query=query, kind=kind, user_id=current_user.id, case_id=case_id, notes=notes)
    flash(f"'{query}' added to watchlist.", "success")
    if case_id is None:
        # Every rescan of this target (watchlist_rescan/finalize_scan) will
        # persist as an investigation with no case_id — surfaced up front so
        # it isn't a surprise later, e.g. on the Dashboard.
        flash("This target isn't linked to a case — its future rescans will "
              "show up as investigations not linked to any case.", "info")
    return redirect(url_for("investigation.watchlist"))


@investigation_bp.route("/watchlist/<int:target_id>/remove", methods=["POST"])
@login_required
def watchlist_remove(target_id):
    from app.repositories.watchlist_repository import remove_target
    remove_target(target_id, user_id=current_user.id)
    flash("Target removed from watchlist.", "success")
    return redirect(url_for("investigation.watchlist"))


@investigation_bp.route("/watchlist/<int:target_id>/rescan", methods=["POST"])
@login_required
def watchlist_rescan(target_id):
    from app.repositories.watchlist_repository import get_target
    from app.services.watchlist_scan_service import finalize_scan
    target = get_target(target_id)
    if not target or target.user_id != current_user.id:
        flash("Target not found.", "error")
        return redirect(url_for("investigation.watchlist"))

    result = {}
    try:
        if target.kind == "ip":
            from app.services import ip_client, virustotal_client, shodan_client
            geo = ip_client.fetch_ip(target.query)
            vt = virustotal_client.fetch_virustotal(target.query)
            shodan = shodan_client.fetch_shodan(target.query)
            result = {"geo": geo, "virustotal": vt, "shodan": shodan}
        elif target.kind == "domain":
            from app.services import rdap_client
            result = rdap_client.fetch_domain(target.query)
        elif target.kind == "email":
            from app.services import hibp_client, hunter_client
            from app.repositories.api_config_repository import get_by_service
            hibp_cfg = get_by_service("hibp")
            hibp_key = hibp_cfg.api_key if hibp_cfg and hibp_cfg.is_enabled else None
            hunter_cfg = get_by_service("hunter")
            hunter_key = hunter_cfg.api_key if hunter_cfg and hunter_cfg.is_enabled else None
            breaches = hibp_client.check_email(target.query, api_key=hibp_key) if hibp_key else {}
            verification = hunter_client.verify_email(target.query, api_key=hunter_key) if hunter_key else {}
            result = {"email": target.query, "breaches": breaches, "verification": verification}
        elif target.kind == "social":
            from app.services import social_client
            result = social_client.search_username(target.query)
        elif target.kind == "crypto":
            from app.services import crypto_client
            result = crypto_client.lookup(target.query)
        elif target.kind == "typosquat":
            from app.services import typosquat_client
            result = typosquat_client.scan_typosquats(target.query)
        elif target.kind == "paste_leak":
            from app.services import paste_client
            pastes = paste_client.check_pastes(target.query)
            result = {"query": target.query, "pastes": pastes if pastes is not None else []}
        else:
            result = {"error": f"Auto-rescan not supported for kind '{target.kind}'."}
    except Exception as exc:
        result = {"error": str(exc)}

    conf = "CONFIRMED" if not result.get("error") else "UNVERIFIED"
    # Hash-diff, persist, alert-flag, log, and notify — shared with the
    # scheduler's automatic rescan so both paths behave identically
    # (app/services/watchlist_scan_service.py).
    changed = finalize_scan(target, result, confidence=conf)

    if changed:
        flash(f"Rescan complete — data changed since last check.", "success")
    else:
        flash(f"Rescan complete — no changes detected.", "info")
    return redirect(url_for("investigation.watchlist"))


@investigation_bp.route("/watchlist/<int:target_id>/dismiss-alert", methods=["POST"])
@login_required
def watchlist_dismiss_alert(target_id):
    from app.repositories.watchlist_repository import get_target, clear_alert
    target = get_target(target_id)
    if not target or target.user_id != current_user.id:
        flash("Target not found.", "error")
        return redirect(url_for("investigation.watchlist"))
    clear_alert(target_id)
    return redirect(url_for("investigation.watchlist"))


# ── Breach & Password Check ──────────────────────────────────────────────────

@investigation_bp.route("/breach", methods=["GET", "POST"])
@login_required
def breach():
    from app.services.hibp_client import check_breaches, check_password_pwned
    from app.utils.audit import log as audit_log

    cases = _cases_for_select()
    case_id = _resolve_case_context()
    email = breaches = error = None
    pwned_count = None
    inv = None

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if email:
            breaches = check_breaches(email)
            if breaches is None:
                error = "Breach checking is disabled, or the lookup failed — see Settings → HIBP."
            audit_log("investigation.run", entity_type="investigation",
                      detail=f"breach check — {email}")
            result_json = json.dumps({"breaches": breaches})
            inv = find_or_update_recent(kind="breach", query=email, result_json=result_json,
                                  user_id=current_user.id, case_id=case_id,
                                  confidence="CONFIRMED" if breaches is not None else "UNVERIFIED")

        if password:
            pwned_count = check_password_pwned(password)

    history = list_by_case_and_kind(case_id, "breach", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/breach.html", email=email,
                           breaches=breaches, pwned_count=pwned_count,
                           error=error, cases=cases, history=history,
                           selected_case_id=case_id, result=inv)


# ── Leak Monitor (Hudson Rock infostealer intelligence) ───────────────────────
# Route/kind names kept as "paste_monitor"/"paste_leak" for backward
# compatibility with existing investigation/watchlist records and
# bookmarked URLs from before the provider switch off psbdmp.ws.

@investigation_bp.route("/paste-monitor", methods=["GET", "POST"])
@login_required
def paste_monitor():
    cases = _cases_for_select()
    case_id = _resolve_case_context()
    query_str = None
    pastes = None
    error = None
    inv = None
    if request.method == "POST":
        query_str = request.form.get("query", "").strip()
        if not query_str:
            flash("A query is required.", "error")
        else:
            from app.services import paste_client
            pastes = paste_client.check_pastes(query_str)

            if pastes is None:
                error = "Leak monitor is disabled. Re-enable it in Settings → PasteMonitor."
            else:
                conf = "CONFIRMED" if pastes else "UNVERIFIED"
                inv = find_or_update_recent(kind="paste_leak", query=query_str, result_json=json.dumps({"query": query_str, "pastes": pastes}),
                                      user_id=current_user.id, case_id=case_id, confidence=conf)
                flash(f"Leak search complete for '{query_str}' — {len(pastes)} hit(s) found.", "success")

    history = list_by_case_and_kind(case_id, "paste_leak", exclude_id=inv.id if inv else None) if case_id else []
    return render_template("investigation/paste_monitor.html", cases=cases, query=query_str, pastes=pastes,
                           error=error, history=history, selected_case_id=case_id, result=inv)


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
    case_id = _resolve_case_context()
    result = None
    inv = None
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if not query:
            flash("Query is required.", "error")
        else:
            try:
                result = plugin.run(query)
            except Exception as exc:
                # An uncaught exception replaces `result` with a bare
                # {"error": ...} blob that carries none of a plugin's
                # normal result shape — persisting that via the upsert
                # below would destroy a previously-stored successful
                # result for this same case/query. A plugin's own
                # normal return value (even one that legitimately
                # includes an "error" key, e.g. a DNS lookup failure) is
                # still persisted as before, matching every other tool
                # route's convention.
                result = {"error": str(exc)}
                flash(f"Plugin '{plugin.label}' failed: {exc}", "error")
            else:
                inv = find_or_update_recent(kind=f"plugin_{plugin.name}", query=query,
                                      result_json=json.dumps(result),
                                      user_id=current_user.id, case_id=case_id)
                flash(f"Plugin '{plugin.label}' completed.", "success")

    history = (list_by_case_and_kind(case_id, f"plugin_{plugin.name}", exclude_id=inv.id if inv else None)
               if case_id else [])
    return render_template("investigation/plugin_run.html",
                           plugin=plugin, cases=cases, result=result,
                           history=history, selected_case_id=case_id)
