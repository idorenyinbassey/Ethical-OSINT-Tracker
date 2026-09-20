from typing import Optional
from sqlmodel import select
from app.models.geocode_cache import GeocodeCache
from app.repositories.base import session_scope


def get_cached(query_text: str) -> Optional[GeocodeCache]:
    with session_scope() as session:
        stmt = select(GeocodeCache).where(GeocodeCache.query_text == query_text)
        row = session.exec(stmt).first()
        if not row:
            return None
        return GeocodeCache(id=row.id, query_text=row.query_text, lat=row.lat, lon=row.lon,
                            display_name=row.display_name, found=row.found, looked_up_at=row.looked_up_at)


def set_cached(query_text: str, lat: float | None, lon: float | None,
               display_name: str, found: bool) -> GeocodeCache:
    """Insert or overwrite the cache entry for `query_text` — a repeated
    lookup of the same address always replaces the old row rather than
    creating a duplicate (query_text is unique)."""
    with session_scope() as session:
        stmt = select(GeocodeCache).where(GeocodeCache.query_text == query_text)
        existing = session.exec(stmt).first()
        if existing:
            existing.lat = lat
            existing.lon = lon
            existing.display_name = display_name
            existing.found = found
            session.add(existing)
            session.flush()
            row = existing
        else:
            row = GeocodeCache(query_text=query_text, lat=lat, lon=lon,
                               display_name=display_name, found=found)
            session.add(row)
            session.flush()
        return GeocodeCache(id=row.id, query_text=row.query_text, lat=row.lat, lon=row.lon,
                            display_name=row.display_name, found=row.found, looked_up_at=row.looked_up_at)
