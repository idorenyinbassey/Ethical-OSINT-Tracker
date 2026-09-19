import io
import csv
import json
import hashlib
import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, abort, session, current_app
from flask_login import login_required, current_user
from app.repositories.case_repository import list_cases, list_cases_for_user, get_case, create_case, update_case, delete_case
from app.repositories.case_comment_repository import add_comment, list_comments
from app.repositories.case_note_repository import add_note, list_notes, delete_note
from app.repositories.investigation_repository import list_by_case, find_related_cases, update_tags, create_investigation, get_investigation
from app.repositories.team_repository import list_teams_for_user
from app.services import report_exporter
from app.utils.authz import can_access_case

cases_bp = Blueprint("cases", __name__, url_prefix="/cases")


def _get_case_with_access(case_id: int, action: str = "read") -> dict | None:
    """Fetch a case and enforce that the current user may perform `action`
    on it (owner, or team-shared per app.utils.authz.can_access_case).

    Returns {"case": case, "investigations": [...]} on success. Returns None
    only when the case does not exist; when the case exists but access is
    denied this raises a 403 via abort() and does not return. Callers
    therefore only need to handle the not-found (None) case.
    """
    case = get_case(case_id)
    if not case:
        return None
    if not can_access_case(case, current_user, action=action):
        abort(403)
    investigations = list_by_case(case_id)
    return {"case": case, "investigations": investigations}


@cases_bp.route("/")
@login_required
def index():
    cases = list_cases_for_user(current_user.id)
    threat_scores = {}
    for case in cases:
        invs = list_by_case(case.id)
        threat_scores[case.id] = _compute_threat_score(invs)
    return render_template("cases/index.html", cases=cases, threat_scores=threat_scores)


@cases_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "medium")

        if not title:
            flash("Title is required.", "error")
            return render_template("cases/new.html")

        case = create_case(title, description, owner_user_id=current_user.id, priority=priority)
        from app.utils.audit import log as audit_log
        audit_log("case.create", entity_type="case", entity_id=getattr(case, "id", None), detail=title)
        flash("Case created.", "success")
        return redirect(url_for("cases.index"))

    return render_template("cases/new.html")


@cases_bp.route("/<int:case_id>", methods=["GET", "POST"])
@login_required
def detail(case_id):
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))

    if request.method == "POST":
        if not can_access_case(case, current_user, action="comment"):
            abort(403)
        body = request.form.get("body", "").strip()
        if body:
            add_comment(case_id=case_id, user_id=current_user.id,
                        username=current_user.username, body=body)
            flash("Comment added.", "success")
        return redirect(url_for("cases.detail", case_id=case_id))

    if not can_access_case(case, current_user, action="read"):
        abort(403)

    session['active_case_id'] = case_id
    investigations = list_by_case(case_id)
    comments = list_comments(case_id)
    notes = list_notes(case_id)
    correlations = find_related_cases(case_id)
    related_cases = []
    for corr in correlations:
        related_case = get_case(corr["case_id"])
        if related_case:
            related_cases.append({"case": related_case, "shared": corr["shared"]})
    threat_score = _compute_threat_score(investigations)
    can_edit = can_access_case(case, current_user, action="edit")
    can_delete = can_access_case(case, current_user, action="delete")
    my_teams = list_teams_for_user(current_user.id)
    # Whichever tool-type group was most recently touched should start open
    # by default — the rest stay collapsed so a case with many scans across
    # many tools stays scannable instead of one long flat list. list_by_case()
    # orders by id (creation order), which isn't the same thing: rerunning an
    # existing scan updates that row in place via find_or_update_recent()
    # without changing its id, so the most-recently-run kind has to be found
    # by updated_at (falling back to created_at for a row never re-run).
    default_open_kind = (
        max(investigations, key=lambda inv: inv.updated_at or inv.created_at).kind
        if investigations else None
    )
    return render_template("cases/detail.html", case=case,
                           investigations=investigations, comments=comments,
                           notes=notes, threat_score=threat_score,
                           related_cases=related_cases, can_edit=can_edit,
                           can_delete=can_delete, my_teams=my_teams,
                           default_open_kind=default_open_kind)


@cases_bp.route("/<int:case_id>/edit", methods=["GET", "POST"])
@login_required
def edit(case_id):
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    if not can_access_case(case, current_user, action="edit"):
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", case.priority)
        status = request.form.get("status", case.status)

        if not title:
            flash("Title is required.", "error")
            return render_template("cases/edit.html", case=case)

        was_closed = case.status == "closed"
        update_case(
            case_id,
            title=title,
            description=description,
            priority=priority,
            status=status,
            updated_at=datetime.datetime.utcnow(),
        )
        # update_case() itself deletes the case's data (atomically, in the
        # same transaction) on any transition into "closed" — including
        # via this form's status dropdown, not just the dedicated Close
        # button. Just audit-log it and adjust the flash message here.
        if status == "closed" and not was_closed:
            _audit_case_close(case_id, title)
            flash("Case updated, closed, and its data deleted.", "success")
        else:
            flash("Case updated.", "success")
        return redirect(url_for("cases.detail", case_id=case_id))

    return render_template("cases/edit.html", case=case)


@cases_bp.route("/<int:case_id>/delete", methods=["POST"])
@login_required
def delete(case_id):
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    if not can_access_case(case, current_user, action="delete"):
        abort(403)
    title = case.title
    delete_case(case_id)
    from app.utils.audit import log as audit_log
    audit_log("case.delete", entity_type="case", entity_id=case_id, detail=title)
    flash("Case deleted.", "success")
    return redirect(url_for("cases.index"))


@cases_bp.route("/<int:case_id>/export/pdf")
@login_required
def export_pdf(case_id):
    result = _get_case_with_access(case_id, action="export")
    if not result:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    case = result["case"]
    investigations = result["investigations"]
    try:
        pdf_bytes = report_exporter.export_pdf(
            case, investigations, app=current_app._get_current_object(), snapshot_user_id=current_user.id
        )
    except RuntimeError as e:
        flash(str(e), "error")
        return redirect(url_for("cases.detail", case_id=case_id))
    from app.utils.audit import log as audit_log
    audit_log("report.export", entity_type="case", entity_id=case_id, detail=f"PDF — {case.title}")
    safe_title = "".join(c for c in case.title if c.isalnum() or c in " -_")[:40].strip()
    filename = f"osint-report-{safe_title or case_id}.pdf"
    return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf",
                     as_attachment=True, download_name=filename)


@cases_bp.route("/<int:case_id>/export/docx")
@login_required
def export_docx(case_id):
    result = _get_case_with_access(case_id, action="export")
    if not result:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    case = result["case"]
    investigations = result["investigations"]
    try:
        docx_bytes = report_exporter.export_docx(
            case, investigations, app=current_app._get_current_object(), snapshot_user_id=current_user.id
        )
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for("cases.detail", case_id=case_id))
    safe_title = "".join(c for c in case.title if c.isalnum() or c in " -_")[:40].strip()
    filename = f"osint-report-{safe_title or case_id}.docx"
    return send_file(
        io.BytesIO(docx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=filename,
    )


@cases_bp.route("/<int:case_id>/export/html")
@login_required
def export_html(case_id):
    result = _get_case_with_access(case_id, action="export")
    if not result:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    case = result["case"]
    investigations = result["investigations"]
    html_str = report_exporter.export_html(
        case, investigations, app=current_app._get_current_object(), snapshot_user_id=current_user.id
    )
    safe_title = "".join(c for c in case.title if c.isalnum() or c in " -_")[:40].strip()
    filename = f"osint-report-{safe_title or case_id}.html"
    return send_file(io.BytesIO(html_str.encode('utf-8')), mimetype="text/html",
                     as_attachment=True, download_name=filename)


@cases_bp.route("/<int:case_id>/export/csv")
@login_required
def export_csv(case_id):
    result = _get_case_with_access(case_id, action="export")
    if not result:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    case = result["case"]
    investigations = result["investigations"]
    csv_bytes = report_exporter.export_csv(case, investigations)
    safe_title = "".join(c for c in case.title if c.isalnum() or c in " -_")[:40].strip()
    filename = f"osint-report-{safe_title or case_id}.csv"
    return send_file(io.BytesIO(csv_bytes), mimetype="text/csv",
                     as_attachment=True, download_name=filename)


@cases_bp.route("/<int:case_id>/export/xlsx")
@login_required
def export_xlsx(case_id):
    result = _get_case_with_access(case_id, action="export")
    if not result:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    case = result["case"]
    investigations = result["investigations"]
    try:
        xlsx_bytes = report_exporter.export_xlsx(case, investigations)
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for("cases.detail", case_id=case_id))
    safe_title = "".join(c for c in case.title if c.isalnum() or c in " -_")[:40].strip()
    filename = f"osint-report-{safe_title or case_id}.xlsx"
    return send_file(io.BytesIO(xlsx_bytes),
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name=filename)


@cases_bp.route("/<int:case_id>/export/stix")
@login_required
def export_stix(case_id):
    result = _get_case_with_access(case_id, action="export")
    if not result:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    case = result["case"]
    investigations = result["investigations"]
    from app.services.stix_export import export_stix as _stix
    from app.utils.audit import log as audit_log
    stix_bytes = _stix(case, investigations)
    audit_log("report.export", entity_type="case", entity_id=case_id,
               detail=f"STIX export — {case.title}")
    safe_title = "".join(c for c in case.title if c.isalnum() or c in " -_")[:40].strip()
    return send_file(io.BytesIO(stix_bytes), mimetype="application/json",
                     as_attachment=True,
                     download_name=f"osint-stix-{safe_title or case_id}.json")


# ── Async report generation ───────────────────────────────────────────────────
import threading, tempfile, uuid as _uuid

_report_jobs: dict = {}  # job_id -> {status, fmt, path, filename, mimetype, error}


def _run_report_job(job_id: str, fmt: str, case, investigations, app=None, snapshot_user_id=None):
    try:
        if fmt == "pdf":
            data = report_exporter.export_pdf(case, investigations, app=app, snapshot_user_id=snapshot_user_id)
            mime = "application/pdf"
            ext = "pdf"
        elif fmt == "docx":
            data = report_exporter.export_docx(case, investigations, app=app, snapshot_user_id=snapshot_user_id)
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
        elif fmt == "html":
            data = report_exporter.export_html(
                case, investigations, app=app, snapshot_user_id=snapshot_user_id
            ).encode("utf-8")
            mime = "text/html"
            ext = "html"
        elif fmt == "xlsx":
            data = report_exporter.export_xlsx(case, investigations)
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        else:
            data = report_exporter.export_csv(case, investigations)
            mime = "text/csv"
            ext = "csv"

        safe_title = "".join(c for c in case.title if c.isalnum() or c in " -_")[:40].strip()
        fd, path = tempfile.mkstemp(suffix=f".{ext}", prefix="osint_report_")
        import os
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        _report_jobs[job_id].update({
            "status": "done", "path": path,
            "filename": f"osint-report-{safe_title or 'case'}.{ext}",
            "mimetype": mime,
        })
    except Exception as exc:
        _report_jobs[job_id].update({"status": "error", "error": str(exc)})


@cases_bp.route("/<int:case_id>/export/start", methods=["POST"])
@login_required
def export_start(case_id):
    case = get_case(case_id)
    if not case:
        from flask import jsonify
        return jsonify({"error": "Not found"}), 404
    if not can_access_case(case, current_user, action="export"):
        from flask import jsonify
        return jsonify({"error": "Forbidden"}), 403
    fmt = request.form.get("fmt", "pdf")
    if fmt not in {"pdf", "docx", "html", "xlsx", "csv"}:
        fmt = "pdf"
    investigations = list_by_case(case_id)
    job_id = str(_uuid.uuid4())
    _report_jobs[job_id] = {"status": "running", "fmt": fmt, "path": None,
                             "filename": None, "mimetype": None, "error": None,
                             "user_id": current_user.id}
    t = threading.Thread(
        target=_run_report_job,
        args=(job_id, fmt, case, investigations, current_app._get_current_object(), current_user.id),
        daemon=True,
    )
    t.start()
    from flask import jsonify
    return jsonify({"job_id": job_id})


@cases_bp.route("/export/status/<job_id>")
@login_required
def export_status(job_id):
    from flask import jsonify
    job = _report_jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404
    # Enforce user ownership of job - IDOR prevention
    if job.get("user_id") != current_user.id:
        return jsonify({"status": "forbidden"}), 403
    return jsonify({"status": job["status"], "error": job.get("error")})


@cases_bp.route("/export/download/<job_id>")
@login_required
def export_download(job_id):
    import os
    job = _report_jobs.get(job_id)
    if not job or job["status"] != "done":
        flash("Report not ready or not found.", "error")
        return redirect(url_for("cases.index"))
    # Enforce user ownership of job - IDOR prevention
    if job.get("user_id") != current_user.id:
        abort(403)
    path = job["path"]
    resp = send_file(path, mimetype=job["mimetype"],
                     as_attachment=True, download_name=job["filename"])
    # Clean up temp file after sending
    @resp.call_on_close
    def _cleanup():
        try:
            os.unlink(path)
        except Exception:
            pass
    _report_jobs.pop(job_id, None)
    return resp


@cases_bp.route("/<int:case_id>/set-active", methods=["POST"])
@login_required
def set_active(case_id):
    case = get_case(case_id)
    if case:
        session['active_case_id'] = case_id
        flash(f"'{case.title}' is now your active case.", "success")
    return redirect(url_for("cases.detail", case_id=case_id))


def _audit_case_close(case_id: int, case_title: str) -> None:
    """Shared audit-log call for any transition into status="closed" — the
    dedicated Close button and the Edit form's status dropdown both funnel
    through this. The actual data deletion happens inside update_case()
    itself, atomically with the status change, not here."""
    from app.utils.audit import log as audit_log
    audit_log("case.close", entity_type="case", entity_id=case_id, detail=case_title)


@cases_bp.route("/<int:case_id>/close", methods=["POST"])
@login_required
def close_case(case_id):
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    if not can_access_case(case, current_user, action="edit"):
        abort(403)
    update_case(case_id, status="closed", updated_at=datetime.datetime.utcnow())
    _audit_case_close(case_id, case.title)
    flash(f"Case '{case.title}' has been closed and its data deleted.", "success")
    return redirect(url_for("cases.detail", case_id=case_id))


@cases_bp.route("/<int:case_id>/reopen", methods=["POST"])
@login_required
def reopen_case(case_id):
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    if not can_access_case(case, current_user, action="edit"):
        abort(403)
    update_case(case_id, status="open", updated_at=datetime.datetime.utcnow())
    flash(f"Case '{case.title}' has been reopened.", "success")
    return redirect(url_for("cases.detail", case_id=case_id))


@cases_bp.route("/<int:case_id>/share", methods=["POST"])
@login_required
def share(case_id):
    """Share (or unshare, if team_id is blank) a case with a team the
    current user belongs to. Only owner/team-owner/team-admin (action
    'edit') may (re)share a case."""
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    if not can_access_case(case, current_user, action="edit"):
        abort(403)

    raw_team_id = request.form.get("team_id", "").strip()
    if not raw_team_id:
        update_case(case_id, team_id=None)
        flash("Case unshared.", "success")
    else:
        try:
            team_id = int(raw_team_id)
        except ValueError:
            flash("Invalid team.", "error")
            return redirect(url_for("cases.detail", case_id=case_id))
        my_team_ids = {t.id for t in list_teams_for_user(current_user.id)}
        if team_id not in my_team_ids:
            flash("You can only share a case with a team you belong to.", "error")
            return redirect(url_for("cases.detail", case_id=case_id))
        update_case(case_id, team_id=team_id)
        from app.utils.audit import log as audit_log
        audit_log("case.share", entity_type="case", entity_id=case_id,
                   detail=f"shared with team {team_id}")
        flash("Case shared with team.", "success")
    return redirect(url_for("cases.detail", case_id=case_id))


# ── Threat Score ──────────────────────────────────────────────────────────────

def _compute_threat_score(investigations) -> int:
    """Return 0-100 threat score from case investigations."""
    score = 0
    for inv in investigations:
        try:
            d = json.loads(inv.result_json or "{}")
        except Exception:
            continue
        if inv.kind == "ip":
            vt = d.get("virustotal") or {}
            stats = (vt.get("data") or {}).get("attributes", {}).get("last_analysis_stats") or vt.get("last_analysis_stats") or {}
            mal = int(stats.get("malicious", 0))
            score += min(mal * 10, 30)
        elif inv.kind == "email":
            breaches = d.get("breaches") or []
            if isinstance(breaches, list):
                score += min(len(breaches) * 5, 25)
        elif inv.kind == "darkweb":
            results = d.get("results") or d.get("data") or []
            if results:
                score += min(len(results) * 3, 20)
        elif inv.kind == "social":
            confirmed = int(d.get("confirmed_count") or 0)
            if confirmed > 10:
                score += 10
            elif confirmed > 5:
                score += 5
        if inv.confidence == "CONFIRMED":
            score += 2
    return min(score, 100)


# ── Case Notes ────────────────────────────────────────────────────────────────

@cases_bp.route("/<int:case_id>/notes", methods=["POST"])
@login_required
def add_case_note(case_id):
    case = get_case(case_id)
    if not case:
        abort(404)
    if not can_access_case(case, current_user, action="comment"):
        abort(403)
    body = request.form.get("body", "").strip()
    kind = request.form.get("kind", "observation")
    valid_kinds = {"observation", "lead", "key_evidence", "follow_up"}
    if kind not in valid_kinds:
        kind = "observation"
    if body:
        add_note(case_id=case_id, user_id=current_user.id,
                 username=current_user.username, kind=kind, body=body)
        flash("Journal entry added.", "success")
    return redirect(url_for("cases.detail", case_id=case_id))


@cases_bp.route("/<int:case_id>/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_case_note(case_id, note_id):
    case = get_case(case_id)
    if not case:
        abort(404)
    if not can_access_case(case, current_user, action="comment"):
        abort(403)
    # Note authors can always delete their own entry; a privileged role
    # (case owner, or team owner/admin on a shared case) can delete anyone's.
    is_privileged = can_access_case(case, current_user, action="edit")
    delete_note(note_id, user_id=current_user.id, force=is_privileged)
    flash("Entry deleted.", "success")
    return redirect(url_for("cases.detail", case_id=case_id))


# ── View a past scan's stored result ──────────────────────────────────────────

@cases_bp.route("/<int:case_id>/investigations/<int:inv_id>")
@login_required
def view_investigation(case_id, inv_id):
    case = get_case(case_id)
    if not case:
        abort(404)
    if not can_access_case(case, current_user, action="read"):
        abort(403)
    inv = get_investigation(inv_id)
    # Must actually belong to this case — without this check, a user with
    # read access to their OWN case could view any investigation on the
    # site just by guessing its inv_id in the URL.
    if not inv or inv.case_id != case_id:
        abort(404)

    result = None
    parse_error = False
    if inv.result_json:
        try:
            result = json.loads(inv.result_json)
        except (ValueError, TypeError):
            parse_error = True

    return render_template("cases/investigation_view.html", case=case, inv=inv,
                           result=result, parse_error=parse_error)


# ── Evidence Tagging ──────────────────────────────────────────────────────────

@cases_bp.route("/<int:case_id>/investigations/<int:inv_id>/tag", methods=["POST"])
@login_required
def tag_investigation(case_id, inv_id):
    case = get_case(case_id)
    if not case:
        abort(404)
    if not can_access_case(case, current_user, action="comment"):
        abort(403)
    tags_raw = request.form.get("tags", "")
    allowed = {"key_evidence", "follow_up", "disputed", "verified", "archived"}
    tags = ",".join(t.strip() for t in tags_raw.split(",") if t.strip() in allowed)
    update_tags(inv_id, tags)
    return redirect(url_for("cases.detail", case_id=case_id))


# ── Bulk Target Import ────────────────────────────────────────────────────────

_VALID_IMPORT_KINDS = {"ip", "domain", "email", "social", "crypto", "phone", "darkweb", "mac", "vehicle", "person"}

@cases_bp.route("/<int:case_id>/import", methods=["POST"])
@login_required
def bulk_import(case_id):
    case = get_case(case_id)
    if not case:
        abort(404)
    if not can_access_case(case, current_user, action="edit"):
        abort(403)

    f = request.files.get("csv_file")
    if not f or not f.filename.endswith(".csv"):
        flash("Please upload a .csv file.", "error")
        return redirect(url_for("cases.detail", case_id=case_id))

    content = f.read().decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(content))

    added = 0
    skipped = 0
    for i, row in enumerate(reader):
        if i >= 50:
            flash("Import capped at 50 rows.", "info")
            break
        kind = (row.get("kind") or row.get("Kind") or "").strip().lower()
        query = (row.get("query") or row.get("Query") or row.get("target") or "").strip()
        if not kind or kind not in _VALID_IMPORT_KINDS or not query:
            skipped += 1
            continue
        create_investigation(
            kind=kind, query=query,
            result_json=json.dumps({"imported": True, "query": query}),
            user_id=current_user.id, case_id=case_id,
            confidence="UNVERIFIED",
        )
        added += 1

    if added:
        flash(f"Imported {added} target(s) as unverified investigations. Run each one to fetch data.", "success")
    if skipped:
        flash(f"{skipped} row(s) skipped (missing/invalid kind or query).", "info")
    return redirect(url_for("cases.detail", case_id=case_id))
