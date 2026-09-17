"""Thin helper — call from any Flask route to write an audit entry."""
from __future__ import annotations


def log(action: str, entity_type: str = "", entity_id: int | None = None, detail: str = "",
        user_id: int | None = None, username: str | None = None) -> None:
    """Write an audit entry.

    By default, user_id/username/ip are derived from the current
    Flask-Login session and request context — the original behavior, and
    still what every route call site relies on. Pass user_id and/or
    username explicitly for calls made outside a request context (e.g.
    the background scheduler, where flask.request/current_user raise),
    so those events still produce a real audit row instead of silently
    no-op'ing through the except-Exception below.
    """
    try:
        from app.repositories.audit_log_repository import add_log

        ip = ""
        if user_id is None and username is None:
            from flask import request as _req
            from flask_login import current_user
            user_id = current_user.id if current_user.is_authenticated else None
            username = current_user.username if current_user.is_authenticated else "anonymous"
            ip = (_req.headers.get("X-Forwarded-For") or _req.remote_addr or "")
            ip = ip.split(",")[0].strip()

        add_log(action=action, user_id=user_id, username=username or "system",
                entity_type=entity_type, entity_id=entity_id,
                detail=detail, ip=ip)
    except Exception:
        pass  # audit failures must never break the application
