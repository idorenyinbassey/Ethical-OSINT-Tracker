from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.repositories.investigation_repository import count_all, count_by_kind, list_recent
from app.repositories.case_repository import list_cases

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    total_investigations = count_all()
    by_kind = count_by_kind()
    recent = list_recent(10)
    all_cases = list_cases(owner_user_id=current_user.id)
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
        by_kind=by_kind,
        recent=recent,
        open_cases=open_cases,
        total_cases=case_stats["total"],
        case_stats=case_stats,
    )
