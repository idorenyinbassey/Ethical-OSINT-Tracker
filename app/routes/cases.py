import io
import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file
from flask_login import login_required, current_user
from app.repositories.case_repository import list_cases, get_case, create_case, update_case, delete_case
from app.repositories.case_comment_repository import add_comment, list_comments
from app.repositories.investigation_repository import list_by_case
from app.services import report_exporter

cases_bp = Blueprint("cases", __name__, url_prefix="/cases")


@cases_bp.route("/")
@login_required
def index():
    cases = list_cases()
    return render_template("cases/index.html", cases=cases)


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

        create_case(title, description, owner_user_id=current_user.id, priority=priority)
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
        body = request.form.get("body", "").strip()
        if body:
            add_comment(case_id=case_id, user_id=current_user.id,
                        username=current_user.username, body=body)
            flash("Comment added.", "success")
        return redirect(url_for("cases.detail", case_id=case_id))

    investigations = list_by_case(case_id)
    comments = list_comments(case_id)
    return render_template("cases/detail.html", case=case,
                           investigations=investigations, comments=comments)


@cases_bp.route("/<int:case_id>/edit", methods=["GET", "POST"])
@login_required
def edit(case_id):
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))

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
    delete_case(case_id)
    flash("Case deleted.", "success")
    return redirect(url_for("cases.index"))


@cases_bp.route("/<int:case_id>/export/pdf")
@login_required
def export_pdf(case_id):
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    investigations = list_by_case(case_id)
    try:
        pdf_bytes = report_exporter.export_pdf(case, investigations)
    except RuntimeError as e:
        flash(str(e), "error")
        return redirect(url_for("cases.detail", case_id=case_id))
    safe_title = "".join(c for c in case.title if c.isalnum() or c in " -_")[:40].strip()
    filename = f"osint-report-{safe_title or case_id}.pdf"
    return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf",
                     as_attachment=True, download_name=filename)


@cases_bp.route("/<int:case_id>/export/docx")
@login_required
def export_docx(case_id):
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    investigations = list_by_case(case_id)
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
