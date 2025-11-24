import httpx
from typing import Optional, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service


@cached(ttl=3600)
async def fetch_ip(ip: str) -> Optional[Dict]:
    """Fetch IP intelligence and geolocation.

    Prefer IPInfo configuration if enabled; otherwise return None and let caller fallback.
    Normalized keys: city,country,asn,org,lat,lon
    """
    cfg = get_by_service("IPInfo")
    if not cfg or not cfg.is_enabled:
        return None
    base = cfg.base_url or "https://ipinfo.io"
    token = cfg.api_key
    url = f"{base.rstrip('/')}/{ip}"
    params = {}
    if token:
        params["token"] = token
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            city = data.get("city")
            country = data.get("country")
            org = data.get("org") or ""
            asn = None
            if org:
                parts = org.split()
                if parts and parts[0].startswith("AS"):
                    asn = parts[0]
            loc = data.get("loc") or ""
            lat = lon = None
            if "," in loc:
                try:
                    lat_s, lon_s = loc.split(",", 1)
                    lat = float(lat_s)
                    lon = float(lon_s)
                except Exception:
                    lat = lon = None
            return {
                "city": city or "",
                "country": country or "",
                "asn": asn or "",
                "org": org,
                "lat": lat,
                "lon": lon,
            }
    except Exception:
        return None
