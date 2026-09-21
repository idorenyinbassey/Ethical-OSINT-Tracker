import secrets
from typing import List, Optional
from sqlmodel import select
from app.models.tracking_link import TrackingLink
from app.models.tracking_hit import TrackingHit
from app.repositories.base import session_scope


def _dl(t: TrackingLink) -> TrackingLink:
    return TrackingLink(id=t.id, token=t.token, label=t.label, case_id=t.case_id,
                        user_id=t.user_id, decoy_mode=t.decoy_mode, redirect_url=t.redirect_url,
                        notes=t.notes, active=t.active, created_at=t.created_at)


def _dh(h: TrackingHit) -> TrackingHit:
    return TrackingHit(id=h.id, link_id=h.link_id, hit_type=h.hit_type,
                       ip=h.ip, user_agent=h.user_agent, referrer=h.referrer,
                       country=h.country, city=h.city, isp=h.isp, lat=h.lat, lon=h.lon,
                       screen=h.screen, timezone=h.timezone, language=h.language,
                       platform=h.platform, browser=h.browser, plugins=h.plugins,
                       gps_lat=h.gps_lat, gps_lon=h.gps_lon, gps_accuracy=h.gps_accuracy,
                       created_at=h.created_at)


def create_link(label: str, user_id: int | None, case_id: int | None = None,
                decoy_mode: str = "404", redirect_url: str = "", notes: str = "") -> TrackingLink:
    with session_scope() as session:
        token = secrets.token_urlsafe(10)
        link = TrackingLink(token=token, label=label, user_id=user_id, case_id=case_id,
                            decoy_mode=decoy_mode, redirect_url=redirect_url, notes=notes)
        session.add(link)
        session.flush()
        return _dl(link)


def get_link_by_token(token: str) -> Optional[TrackingLink]:
    with session_scope() as session:
        row = session.exec(select(TrackingLink).where(TrackingLink.token == token)).first()
        return _dl(row) if row else None


def get_link(link_id: int) -> Optional[TrackingLink]:
    with session_scope() as session:
        row = session.get(TrackingLink, link_id)
        return _dl(row) if row else None


def list_links(user_id: int | None = None) -> List[TrackingLink]:
    with session_scope() as session:
        stmt = select(TrackingLink).order_by(TrackingLink.created_at.desc())
        if user_id:
            stmt = stmt.where(TrackingLink.user_id == user_id)
        return [_dl(r) for r in session.exec(stmt).all()]


def list_links_by_case(case_id: int) -> List[TrackingLink]:
    """All tracking links attached to a case, regardless of which team
    member created them — mirrors investigation_repository.list_by_case's
    unscoped-by-user semantics. Caller (graph_data()) must already have
    checked the requesting user has read access to this case."""
    with session_scope() as session:
        stmt = (
            select(TrackingLink)
            .where(TrackingLink.case_id == case_id)
            .order_by(TrackingLink.created_at.desc())
        )
        return [_dl(r) for r in session.exec(stmt).all()]


def update_link(link_id: int, label: str, decoy_mode: str, redirect_url: str, notes: str) -> bool:
    with session_scope() as session:
        link = session.get(TrackingLink, link_id)
        if not link:
            return False
        link.label = label
        link.decoy_mode = decoy_mode
        link.redirect_url = redirect_url
        link.notes = notes
        session.add(link)
        return True


def set_active(link_id: int, active: bool) -> bool:
    """Pause or resume a link without touching its hit history — the only
    way to stop a link from recording new hits used to be deleting it
    outright, which threw away everything it had already captured."""
    with session_scope() as session:
        link = session.get(TrackingLink, link_id)
        if not link:
            return False
        link.active = active
        session.add(link)
        return True


def delete_link(link_id: int) -> None:
    with session_scope() as session:
        for hit in session.exec(select(TrackingHit).where(TrackingHit.link_id == link_id)).all():
            session.delete(hit)
        link = session.get(TrackingLink, link_id)
        if link:
            session.delete(link)


def record_hit(link_id: int, hit_type: str = "link", **kwargs) -> TrackingHit:
    with session_scope() as session:
        hit = TrackingHit(link_id=link_id, hit_type=hit_type, **kwargs)
        session.add(hit)
        session.flush()
        return _dh(hit)


def update_hit_fingerprint(hit_id: int, **kwargs) -> None:
    with session_scope() as session:
        hit = session.get(TrackingHit, hit_id)
        if hit:
            for k, v in kwargs.items():
                if hasattr(hit, k):
                    setattr(hit, k, v)
            session.add(hit)


def list_hits(link_id: int, limit: int | None = 100, offset: int = 0) -> List[TrackingHit]:
    """Newest-first hits for a link. Defaults to the newest 100 — a link
    left running for a while can accumulate far more hits than a single
    page should ever try to render or poll at once. Pass limit=None for
    the full history (e.g. a case backup export)."""
    with session_scope() as session:
        stmt = (
            select(TrackingHit).where(TrackingHit.link_id == link_id)
            .order_by(TrackingHit.created_at.desc())
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = session.exec(stmt).all()
        return [_dh(h) for h in rows]


def count_hits(link_id: int) -> int:
    with session_scope() as session:
        return len(session.exec(select(TrackingHit).where(TrackingHit.link_id == link_id)).all())
