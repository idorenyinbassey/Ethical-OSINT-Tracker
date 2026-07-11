import logging
import httpx
from typing import Optional, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service

logger = logging.getLogger(__name__)


@cached(ttl=21600)
def fetch_virustotal(ip: str) -> Optional[Dict]:
    """Fetch VirusTotal threat intelligence for an IP address. Returns None if not configured."""
    cfg = get_by_service("VirusTotal")
    if not cfg or not cfg.is_enabled or not cfg.api_key:
        return None

    base = cfg.base_url or "https://www.virustotal.com/api/v3"
    url = f"{base.rstrip('/')}/ip_addresses/{ip}"

    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(url, headers={"x-apikey": cfg.api_key})
            if r.status_code == 404:
                return {
                    "ip": ip, "malicious_count": 0, "suspicious_count": 0,
                    "harmless_count": 0, "total_engines": 0, "community_score": 0,
                    "reputation": 0, "categories": [], "malware_detections": [],
                    "last_analysis_date": "Never", "whois": "",
                }
            r.raise_for_status()
            data = r.json()
            attributes = data.get("data", {}).get("attributes", {})
            stats = attributes.get("last_analysis_stats", {})
            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            harmless = stats.get("harmless", 0)
            undetected = stats.get("undetected", 0)
            total = malicious + suspicious + harmless + undetected
            detections = [
                {"vendor": v, "result": d.get("result", ""), "category": d.get("category", "")}
                for v, d in attributes.get("last_analysis_results", {}).items()
                if d.get("category") in ("malicious", "suspicious")
            ]
            reputation = attributes.get("reputation", 0)
            community_score = -75 if malicious > 5 else (-25 if malicious > 0 else min(reputation, 100))
            return {
                "ip": ip,
                "malicious_count": malicious,
                "suspicious_count": suspicious,
                "harmless_count": harmless,
                "total_engines": total,
                "community_score": community_score,
                "reputation": reputation,
                "categories": list(attributes.get("categories", {}).values()),
                "malware_detections": detections,
                "last_analysis_date": attributes.get("last_analysis_date", "Unknown"),
                "whois": attributes.get("whois", ""),
            }
    except httpx.TimeoutException:
        logger.error("VirusTotal fetch timed out for %s", ip)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("VirusTotal HTTP %s for %s", e.response.status_code, ip)
        return None
    except Exception:
        logger.exception("VirusTotal fetch failed for %s", ip)
        return None
