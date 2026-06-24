import datetime
from typing import List, Optional
from sqlmodel import select
from app.models.watchlist import WatchlistTarget
from app.repositories.base import session_scope


def _detach(w: WatchlistTarget) -> WatchlistTarget:
    return WatchlistTarget(
        id=w.id, query=w.query, kind=w.kind, user_id=w.user_id,
        case_id=w.case_id, notes=w.notes, created_at=w.created_at,
        last_checked=w.last_checked, last_result_hash=w.last_result_hash,
        has_alert=getattr(w, "has_alert", False),
        alert_message=getattr(w, "alert_message", ""),
    )


def add_target(query: str, kind: str, user_id: int | None,
               case_id: int | None = None, notes: str = "") -> WatchlistTarget:
    with session_scope() as session:
        target = WatchlistTarget(query=query, kind=kind, user_id=user_id,
                                  case_id=case_id, notes=notes)
        session.add(target)
        session.flush()
        return _detach(target)


def list_targets(user_id: int | None = None) -> List[WatchlistTarget]:
    with session_scope() as session:
        stmt = select(WatchlistTarget)
        if user_id is not None:
            stmt = stmt.where(WatchlistTarget.user_id == user_id)
        stmt = stmt.order_by(WatchlistTarget.created_at.desc())
        return [_detach(w) for w in session.exec(stmt).all()]


def get_target(target_id: int) -> Optional[WatchlistTarget]:
    with session_scope() as session:
        w = session.get(WatchlistTarget, target_id)
        return _detach(w) if w else None


def remove_target(target_id: int, user_id: int | None) -> bool:
    with session_scope() as session:
        w = session.get(WatchlistTarget, target_id)
        if not w:
            return False
        if user_id and w.user_id and w.user_id != user_id:
            return False
        session.delete(w)
        return True


def update_checked(target_id: int, result_hash: str) -> None:
    with session_scope() as session:
        w = session.get(WatchlistTarget, target_id)
        if w:
            w.last_checked = datetime.datetime.utcnow()
            w.last_result_hash = result_hash
            session.add(w)


def set_alert(target_id: int, message: str) -> None:
    with session_scope() as session:
        w = session.get(WatchlistTarget, target_id)
        if w:
            w.has_alert = True
            w.alert_message = message
            session.add(w)


def clear_alert(target_id: int) -> None:
    with session_scope() as session:
        w = session.get(WatchlistTarget, target_id)
        if w:
            w.has_alert = False
            w.alert_message = ""
            session.add(w)


def list_all_targets() -> List[WatchlistTarget]:
    """Return all targets across all users — used by scheduler only."""
    with session_scope() as session:
        return [_detach(w) for w in session.exec(select(WatchlistTarget)).all()]
