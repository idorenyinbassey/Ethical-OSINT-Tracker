from typing import List, Dict, Optional
from sqlmodel import select, func, delete
from datetime import datetime, timedelta
from app.models.investigation import Investigation
# Ensure user model is imported so SQLAlchemy knows about the referenced `user` table
from app.models.user import User  # noqa: F401
from app.repositories.base import session_scope


def _detach(inv: Investigation) -> Investigation:
    """Return a plain detached copy with all fields copied."""
    return Investigation(
        id=inv.id, kind=inv.kind, query=inv.query,
        created_at=inv.created_at, updated_at=inv.updated_at,
        result_json=inv.result_json, confidence=inv.confidence,
        tags=inv.tags or "",
        user_id=inv.user_id, case_id=inv.case_id,
    )


def create_investigation(kind: str, query: str, result_json: str,
                          user_id: int | None, case_id: int | None = None,
                          confidence: str = "UNVERIFIED") -> Investigation:
    with session_scope() as session:
        inv = Investigation(kind=kind, query=query, result_json=result_json,
                            user_id=user_id, case_id=case_id, confidence=confidence)
        session.add(inv)
        session.flush()
        return _detach(inv)


def find_or_update_recent(kind: str, query: str, result_json: str,
                           user_id: int | None, case_id: int | None = None,
                           confidence: str = "UNVERIFIED") -> Investigation:
    """Upsert: re-running the same tool/query in the same case, as the same
    user, always updates the existing row in place rather than creating a
    sibling — no age limit, so this holds regardless of how long ago the
    original run was. `created_at` is left untouched (it's the case's own
    "first investigated" timestamp); `updated_at` records the refresh.

    Matching requires `user_id` too, so two different users running the
    same query in a case they both have access to don't silently overwrite
    each other's result. `query` is compared case/whitespace-insensitively
    (mirroring find_related_cases()'s normalization below) so
    "8.8.8.8 " or "Example.com" don't spawn a sibling row next to an
    existing "8.8.8.8"/"example.com".

    Investigations not attached to a case (case_id is None) are never
    deduped — each run is a fully separate, ad-hoc row.
    """
    if case_id is None:
        return create_investigation(kind=kind, query=query, result_json=result_json,
                                    user_id=user_id, case_id=None, confidence=confidence)
    normalized_query = query.strip().lower()
    with session_scope() as session:
        existing = session.exec(
            select(Investigation)
            .where(Investigation.case_id == case_id)
            .where(Investigation.user_id == user_id)
            .where(Investigation.kind == kind)
            .where(func.lower(func.trim(Investigation.query)) == normalized_query)
            .order_by(Investigation.created_at.desc())
        ).first()
        if existing:
            existing.result_json = result_json
            existing.updated_at = datetime.utcnow()
            existing.confidence = confidence
            session.add(existing)
            session.flush()
            return _detach(existing)
        inv = Investigation(kind=kind, query=query, result_json=result_json,
                            user_id=user_id, case_id=case_id, confidence=confidence)
        session.add(inv)
        session.flush()
        return _detach(inv)


def update_tags(inv_id: int, tags: str) -> None:
    with session_scope() as session:
        inv = session.get(Investigation, inv_id)
        if inv:
            inv.tags = tags
            session.add(inv)


def list_recent(limit: int = 25, user_id: int | None = None) -> List[Investigation]:
    """Return most recent investigations, scoped to a single user when given.

    Scoping to `user_id` prevents cross-user PII exposure on the dashboard
    (Issue #15): query strings can contain emails/phone numbers, so a user must
    only ever see their own recent investigations.
    """
    with session_scope() as session:
        stmt = select(Investigation)
        if user_id is not None:
            stmt = stmt.where(Investigation.user_id == user_id)
        stmt = stmt.order_by(Investigation.id.desc()).limit(limit)
        results = session.exec(stmt).all()
        return [_detach(inv) for inv in results]


def count_all(user_id: int | None = None) -> int:
    """Count total investigations, scoped to a single user when given."""
    with session_scope() as session:
        stmt = select(func.count(Investigation.id))
        if user_id is not None:
            stmt = stmt.where(Investigation.user_id == user_id)
        return session.exec(stmt).one()


def count_ad_hoc(user_id: int | None = None) -> int:
    """Count investigations never linked to any case (case_id IS NULL).
    These survive every case delete/close untouched, since they were
    never scoped to a case in the first place — the Dashboard surfaces
    this count so "Total Investigations" next to "Total Cases: 0" isn't
    confusing after every case has been deleted."""
    with session_scope() as session:
        stmt = select(func.count(Investigation.id)).where(Investigation.case_id.is_(None))
        if user_id is not None:
            stmt = stmt.where(Investigation.user_id == user_id)
        return session.exec(stmt).one()


def aggregate_by_day(days: int = 7, user_id: int | None = None) -> Dict[datetime.date, int]:
    """Count investigations grouped by date for last N days, optionally per user."""
    with session_scope() as session:
        # created_at is stored as naive UTC (Investigation model default is
        # datetime.utcnow), so compare against UTC — not local now() — to avoid
        # timezone-offset errors.
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = select(Investigation).where(Investigation.created_at >= cutoff)
        if user_id is not None:
            stmt = stmt.where(Investigation.user_id == user_id)
        records = session.exec(stmt).all()

        counts = {}
        for inv in records:
            date_key = inv.created_at.date()
            counts[date_key] = counts.get(date_key, 0) + 1
        return counts


def count_by_kind(user_id: int | None = None) -> Dict[str, int]:
    """Count investigations grouped by kind, scoped to a single user when given."""
    with session_scope() as session:
        stmt = select(Investigation.kind, func.count(Investigation.id))
        if user_id is not None:
            stmt = stmt.where(Investigation.user_id == user_id)
        stmt = stmt.group_by(Investigation.kind)
        results = session.exec(stmt).all()
        return {kind: count for kind, count in results}


def purge_old_investigations(retention_days: int) -> int:
    """Delete investigations not touched in `retention_days` (Issue #15
    retention).

    Returns the number of rows deleted. A non-positive retention_days disables
    purging (returns 0) so operators can opt out by setting RETENTION_DAYS<=0.

    Purges on the more recent of `created_at`/`updated_at`, not `created_at`
    alone: find_or_update_recent() deliberately leaves `created_at` at the
    row's original first-run timestamp forever (with no age limit on
    matching), so a long-lived case's investigation that was refreshed
    today, but first created a year ago, must not be swept away at the
    next purge just because its `created_at` predates the cutoff.
    """
    if retention_days is None or retention_days <= 0:
        return 0
    # created_at/updated_at are naive UTC (see Investigation model default).
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    with session_scope() as session:
        # Single bulk DELETE rather than loading and deleting row-by-row.
        result = session.exec(
            delete(Investigation).where(
                func.coalesce(Investigation.updated_at, Investigation.created_at) < cutoff
            )
        )
        return result.rowcount or 0


def get_investigation(inv_id: int) -> Optional[Investigation]:
    with session_scope() as session:
        inv = session.get(Investigation, inv_id)
        return _detach(inv) if inv else None


def list_by_case(case_id: int) -> List[Investigation]:
    with session_scope() as session:
        stmt = select(Investigation).where(Investigation.case_id == case_id).order_by(Investigation.id.desc())
        results = session.exec(stmt).all()
        return [_detach(inv) for inv in results]


def list_by_case_and_kind(case_id: int, kind: str, exclude_id: int | None = None) -> List[Investigation]:
    """One tool's past investigations in one case, newest first — powers
    each tool page's "previous results in this case" section. exclude_id
    omits the just-run/just-updated result, which is already shown
    separately, front and center, so it doesn't also appear in history."""
    with session_scope() as session:
        stmt = (
            select(Investigation)
            .where(Investigation.case_id == case_id)
            .where(Investigation.kind == kind)
            .order_by(Investigation.created_at.desc())
        )
        if exclude_id is not None:
            stmt = stmt.where(Investigation.id != exclude_id)
        results = session.exec(stmt).all()
        return [_detach(inv) for inv in results]


def list_all(user_id: int | None = None) -> List[Investigation]:
    """Return all investigations, optionally filtered to a single user."""
    with session_scope() as session:
        stmt = select(Investigation)
        if user_id is not None:
            stmt = stmt.where(Investigation.user_id == user_id)
        results = session.exec(stmt).all()
        return [_detach(inv) for inv in results]


def find_related_cases(case_id: int) -> List[Dict]:
    """Return other cases that share investigation queries with this case."""
    with session_scope() as session:
        this_invs = session.exec(
            select(Investigation).where(Investigation.case_id == case_id)
        ).all()
        # Match on (query, kind) pairs to avoid false correlations between
        # different tool types that share the same query string.
        query_kinds = {
            (inv.query.strip().lower(), inv.kind)
            for inv in this_invs if inv.query and inv.query.strip()
        }
        if not query_kinds:
            return []
        all_invs = session.exec(select(Investigation)).all()
        related: Dict[int, list] = {}
        for inv in all_invs:
            if inv.case_id is None or inv.case_id == case_id:
                continue
            if inv.query and (inv.query.strip().lower(), inv.kind) in query_kinds:
                cid = inv.case_id
                if cid not in related:
                    related[cid] = []
                related[cid].append({"query": inv.query, "kind": inv.kind})
        return [{"case_id": cid, "shared": items} for cid, items in related.items()]
