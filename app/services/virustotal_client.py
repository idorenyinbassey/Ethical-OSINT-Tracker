"""VirusTotal API client for IP reputation and threat intelligence.

VirusTotal aggregates data from multiple antivirus engines and security
vendors to provide threat intelligence on IPs, domains, files, and URLs.

Free tier: 4 requests/minute, 500 requests/day
API docs: https://developers.virustotal.com/reference/overview
"""
import random
import hashlib
import httpx
from typing import Optional, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service


def _get_seed(ip: str) -> int:
    """Generate deterministic seed from IP for consistent mock data."""
    return int(hashlib.sha256(ip.encode()).hexdigest(), 16) % (10**8)


def _mock_virustotal_data(ip: str) -> Dict:
    """Generate deterministic mock VirusTotal data for development/fallback."""
    seed = _get_seed(ip)
    rng = random.Random(seed)
    
    # Malicious detection count (0-10)
    malicious_count = rng.randint(0, 10)
    suspicious_count = rng.randint(0, 5)
    
    # Total engines scanned
    total_engines = 90
    
    # Detected categories
    categories = []
    if malicious_count > 0:
        potential_categories = ["malware", "phishing", "spam", "botnet", "c2", "scanner"]
        categories = rng.sample(potential_categories, min(malicious_count, len(potential_categories)))
    
    # Community score (-100 to 100, negative = bad)
    if malicious_count > 5:
        community_score = rng.randint(-100, -50)
    elif malicious_count > 0:
        community_score = rng.randint(-50, 0)
    else:
        community_score = rng.randint(0, 100)
    
    # Mock detection vendors
    vendors = [
        "Kaspersky", "Bitdefender", "ESET", "Sophos", "Avast",
        "AVG", "McAfee", "Norton", "Trend Micro", "F-Secure"
    ]
    
    malware_detections = []
    if malicious_count > 0:
        selected_vendors = rng.sample(vendors, min(malicious_count, len(vendors)))
        for vendor in selected_vendors:
            malware_detections.append({
                "vendor": vendor,
                "result": rng.choice(["malware", "malicious", "suspicious", "phishing"]),
                "category": rng.choice(categories) if categories else "malicious"
            })
    
    # Mock reputation
    reputation = malicious_count
    
    return {
        "ip": ip,
        "malicious_count": malicious_count,
        "suspicious_count": suspicious_count,
        "harmless_count": total_engines - malicious_count - suspicious_count,
        "total_engines": total_engines,
        "community_score": community_score,
        "reputation": reputation,
        "categories": categories,
        "malware_detections": malware_detections,
        "last_analysis_date": "2024-11-25",
        "whois": f"Mock WHOIS data for {ip}",
    }


@cached(ttl=21600)  # Cache for 6 hours
async def fetch_virustotal(ip: str) -> Optional[Dict]:
    """Fetch VirusTotal threat intelligence for an IP address.

    Returns malware detections, community reputation, and threat categories.
    Falls back to deterministic mock data if API unavailable or errors occur.

    Args:
        ip: IP address to lookup

    Returns:
        Dict with keys: ip, malicious_count, suspicious_count, harmless_count,
        total_engines, community_score, reputation, categories, malware_detections,
        last_analysis_date, whois
    """
    cfg = get_by_service("VirusTotal")
    
    # If VirusTotal not configured or disabled, return mock data
    if not cfg or not cfg.is_enabled or not cfg.api_key:
        return _mock_virustotal_data(ip)
    
    base = cfg.base_url or "https://www.virustotal.com/api/v3"
    api_key = cfg.api_key
    url = f"{base.rstrip('/')}/ip_addresses/{ip}"
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            headers = {"x-apikey": api_key}
            r = await client.get(url, headers=headers)
            
            # Handle specific error codes
            if r.status_code == 401:
                # Invalid API key - return mock
                return _mock_virustotal_data(ip)
            
            if r.status_code == 403:
                # Access forbidden - return mock
                return _mock_virustotal_data(ip)
            
            if r.status_code == 404:
                # IP not found - return clean data
                return {
                    "ip": ip,
                    "malicious_count": 0,
                    "suspicious_count": 0,
                    "harmless_count": 0,
                    "total_engines": 0,
                    "community_score": 0,
                    "reputation": 0,
                    "categories": [],
                    "malware_detections": [],
                    "last_analysis_date": "Never",
                    "whois": "",
                    "note": "No data available in VirusTotal for this IP"
                }
            
            if r.status_code == 429:
                # Rate limit exceeded (4 req/min free tier) - return mock
                return _mock_virustotal_data(ip)
            
            r.raise_for_status()
            data = r.json()
            
            # Parse VirusTotal response
            attributes = data.get("data", {}).get("attributes", {})
            stats = attributes.get("last_analysis_stats", {})
            
            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            harmless = stats.get("harmless", 0)
            undetected = stats.get("undetected", 0)
            total = malicious + suspicious + harmless + undetected
            
            # Parse detection results
            results = attributes.get("last_analysis_results", {})
            detections = []
            for vendor, details in results.items():
                if details.get("category") in ["malicious", "suspicious"]:
                    detections.append({
                        "vendor": vendor,
                        "result": details.get("result", ""),
                        "category": details.get("category", "")
                    })
            
            # Get categories
            categories = list(attributes.get("categories", {}).values())
            
            # Community score and reputation
            reputation = attributes.get("reputation", 0)
            # VirusTotal doesn't have a single "community score" field,
            # we derive it from reputation and stats
            if malicious > 5:
                community_score = -75
            elif malicious > 0:
                community_score = -25
            else:
                community_score = min(reputation, 100)
            
            return {
                "ip": ip,
                "malicious_count": malicious,
                "suspicious_count": suspicious,
                "harmless_count": harmless,
                "total_engines": total,
                "community_score": community_score,
                "reputation": reputation,
                "categories": categories,
                "malware_detections": detections,
                "last_analysis_date": attributes.get("last_analysis_date", "Unknown"),
                "whois": attributes.get("whois", ""),
            }
    
    except httpx.TimeoutException:
        # Network timeout - return mock
        return _mock_virustotal_data(ip)
    except Exception:
        # Any other error - return mock
        return _mock_virustotal_data(ip)
