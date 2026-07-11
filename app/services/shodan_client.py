import logging
import httpx
from typing import Optional, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service

logger = logging.getLogger(__name__)


@cached(ttl=3600)
def fetch_shodan(ip: str) -> Optional[Dict]:
    """Fetch Shodan intelligence for an IP address. Returns None if not configured."""
    cfg = get_by_service("Shodan")
    if not cfg or not cfg.is_enabled or not cfg.api_key:
        return None

    base = cfg.base_url or "https://api.shodan.io"
    url = f"{base.rstrip('/')}/shodan/host/{ip}"

    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(url, params={"key": cfg.api_key})
            if r.status_code == 404:
                return {
                    "ip": ip, "open_ports": [], "detected_services": [],
                    "organization": "Unknown", "last_seen": "Never",
                    "vulnerabilities": [], "hostnames": [], "tags": [],
                }
            r.raise_for_status()
            data = r.json()
            services = []
            open_ports = []
            for item in data.get("data", []):
                port = item.get("port")
                if port:
                    open_ports.append(port)
                    services.append({
                        "port": port,
                        "service": item.get("_shodan", {}).get("module", "Unknown"),
                        "banner": item.get("data", "")[:100],
                        "protocol": item.get("transport", "tcp"),
                    })
            vulns = []
            for item in data.get("data", []):
                vulns.extend(item.get("vulns", []))
            return {
                "ip": ip,
                "open_ports": list(set(open_ports)),
                "detected_services": services,
                "organization": data.get("org", "Unknown"),
                "last_seen": data.get("last_update", "Unknown"),
                "vulnerabilities": list(set(vulns)),
                "hostnames": data.get("hostnames", []),
                "tags": data.get("tags", []),
            }
    except httpx.TimeoutException:
        logger.error("Shodan fetch timed out for %s", ip)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Shodan HTTP %s for %s", e.response.status_code, ip)
        return None
    except Exception:
        logger.exception("Shodan fetch failed for %s", ip)
        return None
