from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.repositories.investigation_repository import count_all, count_by_kind, count_ad_hoc, list_recent
from app.repositories.case_repository import list_cases_for_user

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    total_investigations = count_all(user_id=current_user.id)
    by_kind = count_by_kind(user_id=current_user.id)
    # Investigations never linked to a case survive every case delete/close
    # untouched (they were never scoped to one) — surfaced here so "Total
    # Investigations" doesn't look contradictory next to "Total Cases: 0".
    ad_hoc_investigations = count_ad_hoc(user_id=current_user.id)
    recent = list_recent(10, user_id=current_user.id)
    # Includes cases shared with any team the user belongs to, not just
    # cases they personally own (app/utils/authz.py has the permission
    # matrix for what a team member may do with a shared case).
    all_cases = list_cases_for_user(current_user.id)
    case_stats = {
        "total": len(all_cases),
        "open": sum(1 for c in all_cases if c.status == "open"),
        "closed": sum(1 for c in all_cases if c.status == "closed"),
        "in_progress": sum(1 for c in all_cases if c.status == "in_progress"),
        "leads": sum(1 for c in all_cases if c.status == "leads"),
    }
    open_cases = case_stats["open"]
    return render_template(
        "dashboard/index.html",
        total_investigations=total_investigations,
        ad_hoc_investigations=ad_hoc_investigations,
        by_kind=by_kind,
        recent=recent,
        open_cases=open_cases,
        total_cases=case_stats["total"],
        case_stats=case_stats,
    )
