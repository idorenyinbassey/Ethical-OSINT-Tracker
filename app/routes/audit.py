import csv
import io

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user

from app.utils.decorators import admin_required

audit_bp = Blueprint("audit", __name__)


@audit_bp.route("/audit")
@login_required
@admin_required
def index():
    from app.repositories.audit_log_repository import list_logs
    action_filter = request.args.get("action", "").strip()
    logs = list_logs(limit=300, action_filter=action_filter)
    action_types = [
        "login", "case.create", "case.delete",
        "investigation.run", "report.export",
        "watchlist.add", "watchlist.remove", "watchlist.alert",
        "tracker.link_created",
    ]
    return render_template("audit/index.html", logs=logs,
                           action_filter=action_filter, action_types=action_types)


@audit_bp.route("/audit/export")
@login_required
@admin_required
def export():
    """Full CSV download of every audit log row — the system log is the
    one thing meant to persist and be downloadable by an admin, per the
    same policy that gates viewing and clearing it."""
    from app.repositories.audit_log_repository import list_all_logs

    logs = list_all_logs()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["created_at", "username", "user_id", "action", "entity_type", "entity_id", "detail", "ip"])
    for log in logs:
        writer.writerow([
            log.created_at.isoformat() if log.created_at else "",
            log.username, log.user_id or "", log.action,
            log.entity_type, log.entity_id or "", log.detail, log.ip,
        ])
    from app.utils.audit import log as audit_log
    audit_log("audit.export", entity_type="audit_log", detail=f"{len(logs)} rows")
    return send_file(io.BytesIO(buf.getvalue().encode("utf-8")), mimetype="text/csv",
                     as_attachment=True, download_name="audit-log.csv")


@audit_bp.route("/audit/clear", methods=["POST"])
@login_required
@admin_required
def clear():
    """Permanently delete every audit log row — an admin's own password
    must be re-entered first, same as a case delete/close, since this is
    equally irreversible."""
    from app.repositories.audit_log_repository import clear_all_logs
    from app.repositories.user_repository import get_by_id
    from app.utils.authz import verify_current_password

    user = get_by_id(current_user.id)
    if not verify_current_password(user, request.form.get("password", "")):
        flash("Incorrect password — audit log was not cleared.", "error")
        return redirect(url_for("audit.index"))

    count = clear_all_logs()
    from app.utils.audit import log as audit_log
    audit_log("audit.clear", entity_type="audit_log", detail=f"{count} rows cleared")
    flash(f"Audit log cleared ({count} entries removed).", "success")
    return redirect(url_for("audit.index"))
