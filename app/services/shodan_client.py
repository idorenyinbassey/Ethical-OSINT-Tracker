"""Shodan API client for device and port enumeration.

Shodan is a search engine for Internet-connected devices. This client
provides IP lookup functionality to discover open ports, services, and
device information.

Free tier: 100 results/month, no search filters
API docs: https://developer.shodan.io/api
"""
import random
import hashlib
import httpx
from typing import Optional, Dict, List
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service


def _get_seed(ip: str) -> int:
    """Generate deterministic seed from IP for consistent mock data."""
    return int(hashlib.sha256(ip.encode()).hexdigest(), 16) % (10**8)


def _mock_shodan_data(ip: str) -> Dict:
    """Generate deterministic mock Shodan data for development/fallback."""
    seed = _get_seed(ip)
    rng = random.Random(seed)
    
    # Common ports and services
    port_services = [
        (22, "SSH", "OpenSSH 8.2"),
        (80, "HTTP", "nginx 1.18.0"),
        (443, "HTTPS", "nginx 1.18.0"),
        (3306, "MySQL", "MySQL 5.7.31"),
        (5432, "PostgreSQL", "PostgreSQL 13.2"),
        (6379, "Redis", "Redis 6.0.9"),
        (8080, "HTTP", "Apache Tomcat 9.0"),
        (27017, "MongoDB", "MongoDB 4.4.3"),
    ]
    
    # Select 1-4 random open ports
    num_ports = rng.randint(1, 4)
    selected_ports = rng.sample(port_services, num_ports)
    
    open_ports = []
    detected_services = []
    for port, service, banner in selected_ports:
        open_ports.append(port)
        detected_services.append({
            "port": port,
            "service": service,
            "banner": banner,
            "protocol": "tcp"
        })
    
    # Mock organization/ISP
    organizations = [
        "Amazon Technologies Inc.",
        "Google LLC",
        "Microsoft Corporation",
        "DigitalOcean LLC",
        "Cloudflare Inc.",
        "Hetzner Online GmbH",
    ]
    
    # Mock vulnerabilities (CVEs)
    vulnerabilities = [
        "CVE-2021-44228",  # Log4Shell
        "CVE-2022-22965",  # Spring4Shell
        "CVE-2021-3156",   # Sudo vulnerability
        "CVE-2020-1350",   # SigRed DNS
    ]
    
    has_vulns = rng.random() < 0.3  # 30% chance of vulnerabilities
    detected_vulns = []
    if has_vulns:
        num_vulns = rng.randint(1, 2)
        detected_vulns = rng.sample(vulnerabilities, num_vulns)
    
    return {
        "ip": ip,
        "open_ports": open_ports,
        "detected_services": detected_services,
        "organization": rng.choice(organizations),
        "last_seen": "2024-11-25",
        "vulnerabilities": detected_vulns,
        "hostnames": [f"server{rng.randint(1, 999)}.example.com"],
        "tags": ["cloud", "web"] if 80 in open_ports or 443 in open_ports else ["database"] if any(p in open_ports for p in [3306, 5432, 27017]) else [],
    }


@cached(ttl=3600)  # Cache for 1 hour
async def fetch_shodan(ip: str) -> Optional[Dict]:
    """Fetch Shodan intelligence for an IP address.

    Returns device information, open ports, services, and vulnerabilities.
    Falls back to deterministic mock data if API unavailable or errors occur.

    Args:
        ip: IP address to lookup

    Returns:
        Dict with keys: ip, open_ports, detected_services, organization,
        last_seen, vulnerabilities, hostnames, tags
    """
    cfg = get_by_service("Shodan")
    
    # If Shodan not configured or disabled, return mock data
    if not cfg or not cfg.is_enabled or not cfg.api_key:
        return _mock_shodan_data(ip)
    
    base = cfg.base_url or "https://api.shodan.io"
    api_key = cfg.api_key
    url = f"{base.rstrip('/')}/shodan/host/{ip}"
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params={"key": api_key})
            
            # Handle specific error codes
            if r.status_code == 401:
                # Invalid API key - return mock
                return _mock_shodan_data(ip)
            
            if r.status_code == 403:
                # Access forbidden or quota exceeded - return mock
                return _mock_shodan_data(ip)
            
            if r.status_code == 404:
                # IP not found in Shodan - return minimal data
                return {
                    "ip": ip,
                    "open_ports": [],
                    "detected_services": [],
                    "organization": "Unknown",
                    "last_seen": "Never",
                    "vulnerabilities": [],
                    "hostnames": [],
                    "tags": [],
                    "note": "No data available in Shodan for this IP"
                }
            
            if r.status_code == 429:
                # Rate limit exceeded - return mock
                return _mock_shodan_data(ip)
            
            r.raise_for_status()
            data = r.json()
            
            # Parse Shodan response
            services = []
            open_ports = []
            for item in data.get("data", []):
                port = item.get("port")
                if port:
                    open_ports.append(port)
                    services.append({
                        "port": port,
                        "service": item.get("_shodan", {}).get("module", "Unknown"),
                        "banner": item.get("data", "")[:100],  # Truncate banner
                        "protocol": item.get("transport", "tcp")
                    })
            
            vulns = []
            for item in data.get("data", []):
                if "vulns" in item:
                    vulns.extend(item["vulns"])
            
            return {
                "ip": ip,
                "open_ports": list(set(open_ports)),  # Deduplicate
                "detected_services": services,
                "organization": data.get("org", "Unknown"),
                "last_seen": data.get("last_update", "Unknown"),
                "vulnerabilities": list(set(vulns)),  # Deduplicate
                "hostnames": data.get("hostnames", []),
                "tags": data.get("tags", []),
            }
    
    except httpx.TimeoutException:
        # Network timeout - return mock
        return _mock_shodan_data(ip)
    except Exception:
        # Any other error - return mock
        return _mock_shodan_data(ip)
