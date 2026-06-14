import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.repositories.case_repository import list_cases, get_case, create_case, update_case, delete_case

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


@cases_bp.route("/<int:case_id>")
@login_required
def detail(case_id):
    case = get_case(case_id)
    if not case:
        flash("Case not found.", "error")
        return redirect(url_for("cases.index"))
    return render_template("cases/detail.html", case=case)


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
