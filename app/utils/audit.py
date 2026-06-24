"""Thin helper — call from any Flask route to write an audit entry."""
from __future__ import annotations


def log(action: str, entity_type: str = "", entity_id: int | None = None, detail: str = "") -> None:
    try:
        from flask import request as _req
        from flask_login import current_user
        from app.repositories.audit_log_repository import add_log

        uid = current_user.id if current_user.is_authenticated else None
        uname = current_user.username if current_user.is_authenticated else "anonymous"
        ip = (_req.headers.get("X-Forwarded-For") or _req.remote_addr or "")
        ip = ip.split(",")[0].strip()
        add_log(action=action, user_id=uid, username=uname,
                entity_type=entity_type, entity_id=entity_id,
                detail=detail, ip=ip)
    except Exception:
        pass  # audit failures must never break the application
