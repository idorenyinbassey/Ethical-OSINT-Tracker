"""IP geolocation — uses ipapi.co (free, HTTPS, no key) as primary source.

ip-api.com is used as HTTP fallback (free tier only supports HTTP).
IPInfo.io is used as a secondary enrichment source when configured.
"""
import logging
import httpx
from typing import Optional, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service

logger = logging.getLogger(__name__)


@cached(ttl=3600)
def fetch_ip(ip: str) -> Optional[Dict]:
    """Return geolocation/ASN data. Tries HTTPS sources first."""
    result = _from_ipapi_co(ip)
    if not result:
        result = _from_ip_api(ip)
    if result:
        ipinfo = _from_ipinfo(ip)
        if ipinfo:
            for k, v in ipinfo.items():
                if v and not result.get(k):
                    result[k] = v
        return result
    return _from_ipinfo(ip)


def _from_ipapi_co(ip: str) -> Optional[Dict]:
    """ipapi.co — free, HTTPS, no key required, 1000 req/day."""
    try:
        with httpx.Client(timeout=6) as client:
            r = client.get(
                f"https://ipapi.co/{ip}/json/",
                headers={"User-Agent": "OSINT-Tracker/1.0"},
            )
            r.raise_for_status()
            d = r.json()
        if d.get("error"):
            return None
        org = d.get("org") or ""
        asn = d.get("asn") or (org.split()[0] if org and org.startswith("AS") else "")
        return {
            "city": d.get("city", ""),
            "region": d.get("region", ""),
            "country": d.get("country_name", ""),
            "country_code": d.get("country_code", ""),
            "isp": d.get("org", ""),
            "org": org,
            "asn": asn,
            "asn_name": d.get("org", "").split(" ", 1)[1] if " " in org else "",
            "lat": d.get("latitude"),
            "lon": d.get("longitude"),
            "zip": d.get("postal", ""),
            "source": "ipapi.co",
        }
    except httpx.TimeoutException:
        logger.error("ipapi.co lookup timed out for %s", ip)
        return None
    except Exception:
        logger.exception("ipapi.co lookup failed for %s", ip)
        return None


def _from_ip_api(ip: str) -> Optional[Dict]:
    """ip-api.com — free tier, 45 req/min, no key needed. HTTP only on free tier."""
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
    except httpx.TimeoutException:
        logger.error("ip-api.com lookup timed out for %s", ip)
        return None
    except Exception:
        logger.exception("ip-api.com lookup failed for %s", ip)
        return None


def _from_ipinfo(ip: str) -> Optional[Dict]:
    """IPInfo.io — optional enrichment, requires API key for full data."""
    cfg = get_by_service("IPInfo")
    if not cfg or not cfg.is_enabled:
        return None
    base = (cfg.base_url or "https://ipinfo.io").rstrip("/")
    from urllib.parse import urlparse
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
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
    except httpx.TimeoutException:
        logger.error("IPInfo.io lookup timed out for %s", ip)
        return None
    except Exception:
        logger.exception("IPInfo.io lookup failed for %s", ip)
        return None
