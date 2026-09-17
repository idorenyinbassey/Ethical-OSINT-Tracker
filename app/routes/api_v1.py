"""Versioned REST API, authenticated by per-user API keys (see
app/models/api_key.py, app/utils/decorators.py::api_key_required).

Deliberately small and read-mostly for v1: list/read cases and their
investigations, read the watchlist, and trigger a watchlist rescan (the
one write endpoint — reusing the exact same scan logic the scheduler and
the browser's manual "Rescan" button use, not a third copy). Creating,
editing, or deleting cases/investigations, team management, and admin
actions are all out of scope for v1 — kept to what a script pulling case
state into another tool actually needs, to keep the new attack surface
minimal.

Fully stateless: no flask_login/session/cookies/CSRF anywhere in this
blueprint (see csrf.exempt(api_v1_bp) in app/__init__.py). Identity comes
from flask.g.api_user, set by the api_key_required decorator.
"""
from flask import Blueprint, jsonify, g
from app.repositories.case_repository import list_cases_for_user, get_case
from app.repositories.investigation_repository import list_by_case, get_investigation
from app.repositories.watchlist_repository import list_targets, get_target
from app.services.watchlist_scan_service import fetch_target_data, finalize_scan
from app.utils.authz import can_access_case
from app.utils.decorators import api_key_required
from app.utils.rate_limiter import check_rate_limit

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _case_dict(case) -> dict:
    return {
        "id": case.id, "title": case.title, "description": case.description,
        "status": case.status, "priority": case.priority,
        "owner_user_id": case.owner_user_id, "team_id": case.team_id,
        "created_at": case.created_at.isoformat() if case.created_at else None,
    }


def _investigation_dict(inv) -> dict:
    return {
        "id": inv.id, "kind": inv.kind, "query": inv.query,
        "confidence": inv.confidence, "tags": inv.tags,
        "case_id": inv.case_id, "user_id": inv.user_id,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        "result": inv.result_json,
    }


def _target_dict(t) -> dict:
    return {
        "id": t.id, "query": t.query, "kind": t.kind, "case_id": t.case_id,
        "notes": t.notes, "last_checked": t.last_checked.isoformat() if t.last_checked else None,
        "has_alert": t.has_alert, "alert_message": t.alert_message,
    }


@api_v1_bp.route("/cases")
@api_key_required
def list_cases_api():
    cases = list_cases_for_user(g.api_user.id)
    return jsonify({"cases": [_case_dict(c) for c in cases]})


@api_v1_bp.route("/cases/<int:case_id>")
@api_key_required
def get_case_api(case_id):
    case = get_case(case_id)
    if not case:
        return jsonify({"error": "Not found"}), 404
    if not can_access_case(case, g.api_user, action="read"):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(_case_dict(case))


@api_v1_bp.route("/cases/<int:case_id>/investigations")
@api_key_required
def list_case_investigations_api(case_id):
    case = get_case(case_id)
    if not case:
        return jsonify({"error": "Not found"}), 404
    if not can_access_case(case, g.api_user, action="read"):
        return jsonify({"error": "Forbidden"}), 403
    investigations = list_by_case(case_id)
    return jsonify({"investigations": [_investigation_dict(i) for i in investigations]})


@api_v1_bp.route("/investigations/<int:inv_id>")
@api_key_required
def get_investigation_api(inv_id):
    inv = get_investigation(inv_id)
    if not inv:
        return jsonify({"error": "Not found"}), 404
    if inv.case_id:
        case = get_case(inv.case_id)
        if not case or not can_access_case(case, g.api_user, action="read"):
            return jsonify({"error": "Forbidden"}), 403
    elif inv.user_id != g.api_user.id:
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(_investigation_dict(inv))


@api_v1_bp.route("/watchlist")
@api_key_required
def list_watchlist_api():
    targets = list_targets(user_id=g.api_user.id)
    return jsonify({"watchlist": [_target_dict(t) for t in targets]})


@api_v1_bp.route("/watchlist/<int:target_id>/rescan", methods=["POST"])
@api_key_required
def rescan_watchlist_api(target_id):
    allowed, _ = check_rate_limit(key=f"apikey:{g.api_key.id}:rescan", max_requests=20, window_seconds=60)
    if not allowed:
        return jsonify({"error": "Rate limit exceeded"}), 429

    target = get_target(target_id)
    if not target or target.user_id != g.api_user.id:
        return jsonify({"error": "Not found"}), 404

    result = fetch_target_data(target)
    conf = "CONFIRMED" if not result.get("error") else "UNVERIFIED"
    changed = finalize_scan(target, result, confidence=conf)
    return jsonify({"changed": changed, "result": result})
