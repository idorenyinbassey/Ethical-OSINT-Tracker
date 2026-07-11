import io
import csv
import json
import hashlib
import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, abort, session
from flask_login import login_required, current_user
from app.repositories.case_repository import list_cases, get_case, create_case, update_case, delete_case
from app.repositories.case_comment_repository import add_comment, list_comments
from app.repositories.case_note_repository import add_note, list_notes, delete_note
from app.repositories.investigation_repository import list_by_case, find_related_cases, update_tags, create_investigation
from app.services import report_exporter

cases_bp = Blueprint("cases", __name__, url_prefix="/cases")


def _get_case_owned_by_user(case_id: int) -> dict | None:
    """Fetch a case and enforce that the current user owns it.

    Returns {"case": case, "investigations": [...]} on success. Returns None
    only when the case does not exist; when the case exists but is owned by
    another user this raises a 403 via abort() and does not return. Callers
    therefore only need to handle the not-found (None) case.
    """
    case = get_case(case_id)
    if not case:
        return None
    if case.owner_user_id != current_user.id:
        abort(403)
    investigations = list_by_case(case_id)
    return {"case": case, "investigations": investigations}


@cases_bp.route("/")
@login_required
def index():
    cases = list_cases(owner_user_id=current_user.id)
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

    # Enforce user ownership - IDOR prevention
    if case.owner_user_id != current_user.id:
        abort(403)

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if body:
            add_comment(case_id=case_id, user_id=current_user.id,
                        username=current_user.username, body=body)
            flash("Comment added.", "success")
        return redirect(url_for("cases.detail", case_id=case_id))

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
    return render_template("cases/detail.html", case=case,
                           investigations=investigations, comments=comments,
                           notes=notes, threat_score=threat_score,
                           related_cases=related_cases)


@cases_bp.route("/<int:case_id>/edit", methods=["GET", "POST"])
@login_required
def edit(case_id):
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    # Enforce user ownership - IDOR prevention
    if case.owner_user_id != current_user.id:
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", case.priority)
        status = request.form.get("status", case.status)

        if not title:
            flash("Title is required.", "error")
            return render_template("cases/edit.html", case=case)

        update_case(
            case_id,
            title=title,
            description=description,
            priority=priority,
            status=status,
            updated_at=datetime.datetime.utcnow(),
        )
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
    # Enforce user ownership - IDOR prevention
    if case.owner_user_id != current_user.id:
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
    result = _get_case_owned_by_user(case_id)
    if not result:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    case = result["case"]
    investigations = result["investigations"]
    try:
        pdf_bytes = report_exporter.export_pdf(case, investigations)
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
    result = _get_case_owned_by_user(case_id)
    if not result:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    case = result["case"]
    investigations = result["investigations"]
    try:
        docx_bytes = report_exporter.export_docx(case, investigations)
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
    result = _get_case_owned_by_user(case_id)
    if not result:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    case = result["case"]
    investigations = result["investigations"]
    html_str = report_exporter.export_html(case, investigations)
    safe_title = "".join(c for c in case.title if c.isalnum() or c in " -_")[:40].strip()
    filename = f"osint-report-{safe_title or case_id}.html"
    return send_file(io.BytesIO(html_str.encode('utf-8')), mimetype="text/html",
                     as_attachment=True, download_name=filename)


@cases_bp.route("/<int:case_id>/export/csv")
@login_required
def export_csv(case_id):
    result = _get_case_owned_by_user(case_id)
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
    result = _get_case_owned_by_user(case_id)
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
    result = _get_case_owned_by_user(case_id)
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


def _run_report_job(job_id: str, fmt: str, case, investigations):
    try:
        if fmt == "pdf":
            data = report_exporter.export_pdf(case, investigations)
            mime = "application/pdf"
            ext = "pdf"
        elif fmt == "docx":
            data = report_exporter.export_docx(case, investigations)
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
        elif fmt == "html":
            data = report_exporter.export_html(case, investigations).encode("utf-8")
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
    # Enforce user ownership - IDOR prevention
    if case.owner_user_id != current_user.id:
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
    t = threading.Thread(target=_run_report_job, args=(job_id, fmt, case, investigations), daemon=True)
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


@cases_bp.route("/<int:case_id>/close", methods=["POST"])
@login_required
def close_case(case_id):
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    if case.owner_user_id and case.owner_user_id != current_user.id:
        abort(403)
    update_case(case_id, status="closed", updated_at=datetime.datetime.utcnow())
    flash(f"Case '{case.title}' has been closed.", "success")
    return redirect(url_for("cases.detail", case_id=case_id))


@cases_bp.route("/<int:case_id>/reopen", methods=["POST"])
@login_required
def reopen_case(case_id):
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    if case.owner_user_id and case.owner_user_id != current_user.id:
        abort(403)
    update_case(case_id, status="open", updated_at=datetime.datetime.utcnow())
    flash(f"Case '{case.title}' has been reopened.", "success")
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
    delete_note(note_id, user_id=current_user.id)
    flash("Entry deleted.", "success")
    return redirect(url_for("cases.detail", case_id=case_id))


# ── Evidence Tagging ──────────────────────────────────────────────────────────

@cases_bp.route("/<int:case_id>/investigations/<int:inv_id>/tag", methods=["POST"])
@login_required
def tag_investigation(case_id, inv_id):
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
    if case.owner_user_id and case.owner_user_id != current_user.id:
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
