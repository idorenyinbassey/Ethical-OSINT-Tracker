"""Shared watchlist-rescan finalization.

Both the background scheduler's automatic 6-hour rescan
(app/utils/scheduler.py) and the user-triggered manual rescan route
(POST /watchlist/<id>/rescan in app/routes/investigation.py) fetch fresh
data for a target using different logic (the scheduler does one cheap
call per kind; the manual route enriches more heavily since a human
explicitly asked for it and is spending their own configured API quota).
What both need to do identically once they have a fresh result — hash it,
persist last_checked/last_result_hash, flip the alert flag on change, log
an investigation record, and fire a notification — lives here, so the two
call sites can't diverge again. Previously the manual route duplicated
(and subtly mis-implemented — see `changed` below) this instead of
sharing it, and never called set_alert at all.
"""
import hashlib
import json
import datetime
import logging

from app.repositories.watchlist_repository import update_checked, set_alert
from app.repositories.investigation_repository import find_or_update_recent
from app.services.notification_service import notify

logger = logging.getLogger(__name__)


def fetch_target_data(target) -> dict:
    """One cheap, free/low-cost fetch per watchlist kind — the "automatic"
    tier used by both the scheduler's 6h rescan and the API's
    /api/v1/watchlist/<id>/rescan endpoint. Deliberately lighter than the
    browser "Rescan" button in app/routes/investigation.py, which enriches
    more heavily (multiple paid-tier services) since a human explicitly
    asked for it and is spending their own configured API quota — an
    unattended trigger firing every few hours (or on demand via a script)
    should not silently burn through the same quota.
    """
    try:
        if target.kind == "ip":
            from app.services import ip_client
            return ip_client.fetch_ip(target.query) or {}
        elif target.kind == "domain":
            from app.services import rdap_client
            return rdap_client.fetch_domain(target.query) or {}
        elif target.kind == "email":
            from app.services import hibp_client
            return {"breaches": hibp_client.check_breaches(target.query)}
        elif target.kind == "social":
            from app.services import social_client
            return social_client.search_username(target.query) or {}
        elif target.kind == "crypto":
            from app.services import crypto_client
            return crypto_client.lookup(target.query) or {}
        elif target.kind == "phone":
            from app.services import numverify_client
            return numverify_client.fetch_phone(target.query) or {}
        elif target.kind == "typosquat":
            from app.services import typosquat_client
            return typosquat_client.scan_typosquats(target.query) or {}
        elif target.kind == "paste_leak":
            from app.services import paste_client
            pastes = paste_client.check_pastes(target.query)
            return {"query": target.query, "pastes": pastes if pastes is not None else []}
        return {"error": f"Auto-rescan not supported for kind '{target.kind}'."}
    except Exception as exc:
        return {"error": str(exc)}


def finalize_scan(target, result: dict, confidence: str = "CONFIRMED") -> bool:
    """Persist a freshly-fetched watchlist result and handle alerting.

    Args:
        target: a WatchlistTarget (as returned by the repository).
        result: the freshly-fetched data for this target.
        confidence: confidence level to log the resulting investigation
            record with (callers may downgrade this, e.g. to
            "UNVERIFIED" when `result` contains an error).

    Returns:
        True if the result changed since the last check. A target's very
        first-ever check never counts as a change (there's nothing to
        diff against yet) — this guard was missing in the old manual
        rescan route, which flashed "data changed" on every target's
        first rescan.
    """
    result_json = json.dumps(result, default=str)
    new_hash = hashlib.sha256(result_json.encode()).hexdigest()[:16]
    changed = bool(target.last_result_hash) and new_hash != target.last_result_hash

    update_checked(target.id, new_hash)

    if changed:
        message = (
            f"Data changed at {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
        )
        set_alert(target.id, message)
        find_or_update_recent(
            kind=target.kind, query=target.query, result_json=result_json,
            user_id=target.user_id, case_id=target.case_id, confidence=confidence,
        )
        try:
            from app.utils.audit import log as audit_log
            audit_log(
                "watchlist.alert", entity_type="watchlist", entity_id=target.id,
                detail=f"{target.kind}:{target.query} changed",
                user_id=target.user_id,
            )
        except Exception:
            pass  # audit failures must never break a rescan
        try:
            notify(
                subject=f"Watchlist alert: {target.query}",
                body=message,
                payload={"target_id": target.id, "kind": target.kind, "query": target.query},
            )
        except Exception:
            logger.exception("Notification dispatch failed for watchlist target %s", target.id)

    return changed
