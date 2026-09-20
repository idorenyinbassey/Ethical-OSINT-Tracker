"""Forward geocoding via Nominatim (OpenStreetMap) — turns a free-text
address string into (lat, lon), so a tool that only produces structured
address text (currently: Company Registry hits) can still plot a
"suspected" location on the map alongside IP geolocation's "approximate"
markers and EXIF GPS's "exact" ones.

Free, no API key, but Nominatim's usage policy caps unauthenticated use
at 1 request/second and requires caching results rather than re-geocoding
the same input repeatedly — every lookup checks
app.repositories.geocode_cache_repository first, and only a genuine
cache miss reaches the network, gated by a small in-process rate limiter
below.
"""
import time

from app.repositories.geocode_cache_repository import get_cached, set_cached
from app.utils.proxy_config import get_http_client

_USER_AGENT = "Ethical-OSINT-Tracker/1.0 (+https://github.com/idorenyinbassey/Ethical-OSINT-Tracker)"
_MIN_INTERVAL = 1.05  # Nominatim's usage policy allows at most 1 request/second.
_last_request_at = 0.0


def geocode(address: str) -> dict | None:
    """Return {"lat": float, "lon": float, "display_name": str} for
    `address`, or None if it couldn't be resolved (blank input, no match,
    or a network/parsing failure — never raises, since a geocoding miss
    should mean one fewer map marker, not a broken page).

    Checks the cache first; a live lookup — whether it finds a result or
    not — is always written back so the exact same address string is
    never geocoded twice.
    """
    normalized = " ".join(address.split()).strip()
    if not normalized:
        return None

    cached = get_cached(normalized)
    if cached is not None:
        if not cached.found:
            return None
        return {"lat": cached.lat, "lon": cached.lon, "display_name": cached.display_name}

    global _last_request_at
    try:
        elapsed = time.monotonic() - _last_request_at
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        with get_http_client(timeout=8) as client:
            resp = client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": normalized, "format": "json", "limit": 1},
                headers={"User-Agent": _USER_AGENT},
            )
        _last_request_at = time.monotonic()
        resp.raise_for_status()
        results = resp.json()
    except Exception:
        return None

    if not results:
        set_cached(normalized, None, None, "", found=False)
        return None

    hit = results[0]
    try:
        lat = float(hit["lat"])
        lon = float(hit["lon"])
    except (KeyError, TypeError, ValueError):
        set_cached(normalized, None, None, "", found=False)
        return None

    display_name = hit.get("display_name", "") or ""
    set_cached(normalized, lat, lon, display_name, found=True)
    return {"lat": lat, "lon": lon, "display_name": display_name}
