import logging
import httpx
from typing import Optional, Dict
from app.services.cache import cached

logger = logging.getLogger(__name__)


def _rdap_parse(data: dict) -> dict:
    registrar = None
    if "entities" in data:
        for ent in data["entities"]:
            roles = ent.get("roles", [])
            if "registrar" in roles:
                v = ent.get("vcardArray", [])
                if isinstance(v, list) and len(v) > 1:
                    for item in v[1]:
                        if len(item) >= 3 and item[0] == "fn":
                            registrar = item[3] if len(item) > 3 else item[2]
                            break
                break

    status = None
    if "status" in data and isinstance(data["status"], list) and data["status"]:
        status = data["status"][0]

    nservers = []
    for ns in data.get("nameservers", []) or []:
        ldhName = ns.get("ldhName")
        if ldhName:
            nservers.append(ldhName)

    created = expires = None
    for ev in data.get("events", []) or []:
        if ev.get("eventAction") == "registration":
            created = ev.get("eventDate")
        if ev.get("eventAction") == "expiration":
            expires = ev.get("eventDate")

    return {
        "registrar": registrar or "Unknown Registrar",
        "status": status or "active",
        "ns": nservers,
        "created": created or "",
        "expires": expires or "",
    }


@cached(ttl=24 * 3600)
def fetch_domain(domain: str) -> Optional[Dict]:
    """Fetch domain registration data from public RDAP (no key required)."""
    urls = [
        f"https://rdap.org/domain/{domain}",
        f"https://www.iana.org/rdap/domain/{domain}",
    ]
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            for url in urls:
                try:
                    r = client.get(url)
                    r.raise_for_status()
                    data = r.json()
                    return _rdap_parse(data)
                except (httpx.HTTPStatusError, httpx.RequestError):
                    continue
    except httpx.TimeoutException:
        logger.error("RDAP lookup timed out for %s", domain)
    except Exception:
        logger.exception("RDAP lookup failed for %s", domain)
    return None
