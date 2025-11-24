from typing import List, Dict
from sqlmodel import select, func
from datetime import datetime, timedelta
from app.models.investigation import Investigation
from app.repositories.base import session_scope


def create_investigation(kind: str, query: str, result_json: str, user_id: int | None) -> Investigation:
    with session_scope() as session:
        inv = Investigation(kind=kind, query=query, result_json=result_json, user_id=user_id)
        session.add(inv)
        session.flush()
        return inv


def list_recent(limit: int = 25) -> List[Investigation]:
    with session_scope() as session:
        stmt = select(Investigation).order_by(Investigation.id.desc()).limit(limit)
        results = session.exec(stmt).all()
        # Eagerly load all attributes before session closes
        return [Investigation(
            id=inv.id,
            kind=inv.kind,
            query=inv.query,
            result_json=inv.result_json,
            user_id=inv.user_id,
            created_at=inv.created_at
        ) for inv in results]


def count_all() -> int:
    """Count total investigations"""
    with session_scope() as session:
        stmt = select(func.count(Investigation.id))
        return session.exec(stmt).one()


def aggregate_by_day(days: int = 7) -> Dict[datetime.date, int]:
    """Count investigations grouped by date for last N days"""
    with session_scope() as session:
        cutoff = datetime.now() - timedelta(days=days)
        stmt = select(Investigation).where(Investigation.created_at >= cutoff)
        records = session.exec(stmt).all()
        
        counts = {}
        for inv in records:
            date_key = inv.created_at.date()
            counts[date_key] = counts.get(date_key, 0) + 1
        return counts


def count_by_kind() -> Dict[str, int]:
    """Count investigations grouped by kind"""
    with session_scope() as session:
        stmt = select(Investigation.kind, func.count(Investigation.id)).group_by(Investigation.kind)
        results = session.exec(stmt).all()
        return {kind: count for kind, count in results}
