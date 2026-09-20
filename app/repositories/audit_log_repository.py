from typing import List, Optional
from sqlmodel import select, delete
from app.models.audit_log import AuditLog
from app.repositories.base import session_scope


def add_log(action: str, user_id: int | None = None, username: str = "",
            entity_type: str = "", entity_id: int | None = None,
            detail: str = "", ip: str = "") -> None:
    with session_scope() as session:
        session.add(AuditLog(action=action, user_id=user_id, username=username,
                             entity_type=entity_type, entity_id=entity_id,
                             detail=detail, ip=ip))


def list_logs(limit: int = 200, action_filter: str = "") -> List[AuditLog]:
    with session_scope() as session:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        if action_filter:
            stmt = stmt.where(AuditLog.action.contains(action_filter))
        rows = session.exec(stmt).all()
        return [AuditLog(id=r.id, user_id=r.user_id, username=r.username,
                         action=r.action, entity_type=r.entity_type,
                         entity_id=r.entity_id, detail=r.detail,
                         ip=r.ip, created_at=r.created_at) for r in rows]


def list_all_logs() -> List[AuditLog]:
    """Every audit log row, oldest first — used for a full export, unlike
    list_logs()'s newest-first, capped-at-`limit` view for the UI."""
    with session_scope() as session:
        stmt = select(AuditLog).order_by(AuditLog.created_at.asc())
        rows = session.exec(stmt).all()
        return [AuditLog(id=r.id, user_id=r.user_id, username=r.username,
                         action=r.action, entity_type=r.entity_type,
                         entity_id=r.entity_id, detail=r.detail,
                         ip=r.ip, created_at=r.created_at) for r in rows]


def clear_all_logs() -> int:
    """Permanently delete every audit log row. Returns the number of rows
    removed. The system/audit log is the one thing meant to persist
    across everything else being deleted — clearing it is therefore an
    admin-only, password-confirmed action in its own right (see
    app/routes/audit.py), not a side effect of any other cleanup."""
    with session_scope() as session:
        result = session.exec(delete(AuditLog))
        return result.rowcount or 0
