from flask import Blueprint, render_template, request
from flask_login import login_required

audit_bp = Blueprint("audit", __name__)


@audit_bp.route("/audit")
@login_required
def index():
    from app.repositories.audit_log_repository import list_logs
    action_filter = request.args.get("action", "").strip()
    logs = list_logs(limit=300, action_filter=action_filter)
    action_types = [
        "login", "case.create", "case.delete",
        "investigation.run", "report.export",
        "watchlist.add", "watchlist.remove",
        "tracker.link_created",
    ]
    return render_template("audit/index.html", logs=logs,
                           action_filter=action_filter, action_types=action_types)
