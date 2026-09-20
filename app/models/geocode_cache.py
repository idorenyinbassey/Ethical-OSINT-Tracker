import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class GeocodeCache(SQLModel, table=True):
    """A cached Nominatim forward-geocode result, keyed by the normalized
    address text that was looked up. Nominatim's usage policy caps
    unauthenticated use at 1 request/second and requires caching results
    rather than re-geocoding the same input repeatedly — this table is
    that cache, not just a performance optimization."""
    __tablename__ = "geocode_cache"
    id: Optional[int] = Field(default=None, primary_key=True)
    query_text: str = Field(index=True, unique=True)
    lat: Optional[float] = Field(default=None)
    lon: Optional[float] = Field(default=None)
    display_name: str = Field(default="")
    # A prior lookup that found nothing is cached too (lat/lon left None) —
    # otherwise a bad/unresolvable address would be re-queried forever.
    found: bool = Field(default=False)
    looked_up_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
