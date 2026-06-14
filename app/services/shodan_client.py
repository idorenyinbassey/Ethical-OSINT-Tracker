import random
import hashlib
import httpx
from typing import Optional, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service


def _get_seed(ip: str) -> int:
    return int(hashlib.sha256(ip.encode()).hexdigest(), 16) % (10**8)


def _mock_shodan_data(ip: str) -> Dict:
    seed = _get_seed(ip)
    rng = random.Random(seed)
    port_services = [
        (22, "SSH", "OpenSSH 8.2"), (80, "HTTP", "nginx 1.18.0"),
        (443, "HTTPS", "nginx 1.18.0"), (3306, "MySQL", "MySQL 5.7.31"),
        (5432, "PostgreSQL", "PostgreSQL 13.2"), (6379, "Redis", "Redis 6.0.9"),
        (8080, "HTTP", "Apache Tomcat 9.0"), (27017, "MongoDB", "MongoDB 4.4.3"),
    ]
    selected = rng.sample(port_services, rng.randint(1, 4))
    open_ports = [p for p, _, _ in selected]
    services = [{"port": p, "service": s, "banner": b, "protocol": "tcp"} for p, s, b in selected]
    orgs = ["Amazon Technologies Inc.", "Google LLC", "Microsoft Corporation",
            "DigitalOcean LLC", "Cloudflare Inc.", "Hetzner Online GmbH"]
    vulnerabilities = []
    if rng.random() < 0.3:
        all_cves = ["CVE-2021-44228", "CVE-2022-22965", "CVE-2021-3156", "CVE-2020-1350"]
        vulnerabilities = rng.sample(all_cves, rng.randint(1, 2))
    return {
        "ip": ip,
        "open_ports": open_ports,
        "detected_services": services,
        "organization": rng.choice(orgs),
        "last_seen": "2024-11-25",
        "vulnerabilities": vulnerabilities,
        "hostnames": [f"server{rng.randint(1, 999)}.example.com"],
        "tags": ["cloud", "web"] if 80 in open_ports or 443 in open_ports else ["database"],
    }


@cached(ttl=3600)
def fetch_shodan(ip: str) -> Optional[Dict]:
    """Fetch Shodan intelligence for an IP address. Falls back to mock data."""
    cfg = get_by_service("Shodan")
    if not cfg or not cfg.is_enabled or not cfg.api_key:
        return _mock_shodan_data(ip)

    base = cfg.base_url or "https://api.shodan.io"
    url = f"{base.rstrip('/')}/shodan/host/{ip}"

    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(url, params={"key": cfg.api_key})
            if r.status_code in (401, 403, 429):
                return _mock_shodan_data(ip)
            if r.status_code == 404:
                return {"ip": ip, "open_ports": [], "detected_services": [], "organization": "Unknown",
                        "last_seen": "Never", "vulnerabilities": [], "hostnames": [], "tags": []}
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
    except Exception:
        return _mock_shodan_data(ip)
