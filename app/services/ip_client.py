"""IP geolocation — uses ip-api.com (free, no API key) as primary source.

IPInfo.io is used as a secondary enrichment source when configured.
"""
import httpx
from typing import Optional, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service


@cached(ttl=3600)
def fetch_ip(ip: str) -> Optional[Dict]:
    """Return geolocation/ASN data. ip-api.com is tried first (free, no key required)."""
    result = _from_ip_api(ip)
    if result:
        ipinfo = _from_ipinfo(ip)
        if ipinfo:
            for k, v in ipinfo.items():
                if v and not result.get(k):
                    result[k] = v
        return result
    return _from_ipinfo(ip)


def _from_ip_api(ip: str) -> Optional[Dict]:
    """ip-api.com — free tier, 45 req/min, no key needed."""
    fields = "status,message,country,countryCode,regionName,city,zip,lat,lon,isp,org,as,asname"
    try:
        with httpx.Client(timeout=6) as client:
            r = client.get(f"http://ip-api.com/json/{ip}", params={"fields": fields})
            r.raise_for_status()
            d = r.json()
        if d.get("status") != "success":
            return None
        asn_full = d.get("as", "")
        asn = asn_full.split()[0] if asn_full else ""
        return {
            "city": d.get("city", ""),
            "region": d.get("regionName", ""),
            "country": d.get("country", ""),
            "country_code": d.get("countryCode", ""),
            "isp": d.get("isp", ""),
            "org": d.get("org", ""),
            "asn": asn,
            "asn_name": d.get("asname", ""),
            "lat": d.get("lat"),
            "lon": d.get("lon"),
            "zip": d.get("zip", ""),
            "source": "ip-api.com",
        }
    except Exception:
        return None


def _from_ipinfo(ip: str) -> Optional[Dict]:
    """IPInfo.io — optional enrichment, requires API key for full data."""
    cfg = get_by_service("IPInfo")
    if not cfg or not cfg.is_enabled:
        return None
    base = (cfg.base_url or "https://ipinfo.io").rstrip("/")
    params: dict = {}
    if cfg.api_key:
        params["token"] = cfg.api_key
    try:
        with httpx.Client(timeout=5) as client:
            r = client.get(f"{base}/{ip}", params=params)
            r.raise_for_status()
            d = r.json()
        org = d.get("org") or ""
        asn = org.split()[0] if org and org.startswith("AS") else ""
        loc = d.get("loc") or ""
        lat = lon = None
        if "," in loc:
            try:
                lat, lon = map(float, loc.split(",", 1))
            except Exception:
                pass
        return {
            "city": d.get("city", ""),
            "country": d.get("country", ""),
            "asn": asn,
            "org": org,
            "lat": lat,
            "lon": lon,
            "source": "IPInfo.io",
        }
    except Exception:
        return None
