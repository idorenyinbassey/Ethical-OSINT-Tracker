import random
import hashlib
import httpx
from typing import Optional, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service


def _get_seed(ip: str) -> int:
    return int(hashlib.sha256(ip.encode()).hexdigest(), 16) % (10**8)


def _mock_virustotal_data(ip: str) -> Dict:
    seed = _get_seed(ip)
    rng = random.Random(seed)
    malicious_count = rng.randint(0, 10)
    suspicious_count = rng.randint(0, 5)
    total_engines = 90
    categories = []
    if malicious_count > 0:
        potential = ["malware", "phishing", "spam", "botnet", "c2", "scanner"]
        categories = rng.sample(potential, min(malicious_count, len(potential)))
    community_score = rng.randint(-100, -50) if malicious_count > 5 else (rng.randint(-50, 0) if malicious_count > 0 else rng.randint(0, 100))
    vendors = ["Kaspersky", "Bitdefender", "ESET", "Sophos", "Avast", "AVG", "McAfee", "Norton", "Trend Micro", "F-Secure"]
    malware_detections = []
    if malicious_count > 0:
        for vendor in rng.sample(vendors, min(malicious_count, len(vendors))):
            malware_detections.append({
                "vendor": vendor,
                "result": rng.choice(["malware", "malicious", "suspicious", "phishing"]),
                "category": rng.choice(categories) if categories else "malicious",
            })
    return {
        "ip": ip,
        "malicious_count": malicious_count,
        "suspicious_count": suspicious_count,
        "harmless_count": total_engines - malicious_count - suspicious_count,
        "total_engines": total_engines,
        "community_score": community_score,
        "reputation": malicious_count,
        "categories": categories,
        "malware_detections": malware_detections,
        "last_analysis_date": "2024-11-25",
        "whois": f"Mock WHOIS data for {ip}",
    }


@cached(ttl=21600)
def fetch_virustotal(ip: str) -> Optional[Dict]:
    """Fetch VirusTotal threat intelligence for an IP address. Falls back to mock data."""
    cfg = get_by_service("VirusTotal")
    if not cfg or not cfg.is_enabled or not cfg.api_key:
        return _mock_virustotal_data(ip)

    base = cfg.base_url or "https://www.virustotal.com/api/v3"
    url = f"{base.rstrip('/')}/ip_addresses/{ip}"

    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(url, headers={"x-apikey": cfg.api_key})
            if r.status_code in (401, 403, 429):
                return _mock_virustotal_data(ip)
            if r.status_code == 404:
                return {"ip": ip, "malicious_count": 0, "suspicious_count": 0, "harmless_count": 0,
                        "total_engines": 0, "community_score": 0, "reputation": 0, "categories": [],
                        "malware_detections": [], "last_analysis_date": "Never", "whois": ""}
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
    except Exception:
        return _mock_virustotal_data(ip)
