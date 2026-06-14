"""Subdomain and DNS scanner — uses crt.sh (Certificate Transparency) + DNS resolution wordlist."""
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.cache import cached
from app.utils.proxy_config import get_http_client

_WORDLIST = [
    "www", "mail", "ftp", "smtp", "pop", "imap", "webmail", "cpanel", "whm",
    "admin", "panel", "dashboard", "portal", "api", "api2", "v1", "v2", "dev",
    "staging", "test", "beta", "alpha", "blog", "shop", "store", "forum",
    "community", "support", "help", "kb", "docs", "wiki", "static", "assets",
    "cdn", "img", "images", "media", "video", "download", "files", "vpn",
    "remote", "ns1", "ns2", "dns", "mx", "relay", "m", "mobile", "app", "web",
    "secure", "ssl", "login", "auth", "git", "gitlab", "ci", "jenkins", "jira",
    "status", "monitor", "grafana", "intranet", "internal", "extranet", "legacy",
    "backup", "old", "new", "demo", "analytics", "tracking", "stats", "crm",
    "erp", "cloud", "db", "database", "uploads", "storage", "s3", "smtp2",
    "mail2", "webmail2", "proxy", "gateway", "lb",
]


def _crt_sh_subdomains(domain: str) -> list[str]:
    subs: set[str] = set()
    try:
        with get_http_client(timeout=20) as client:
            r = client.get(
                "https://crt.sh/",
                params={"q": f"%.{domain}", "output": "json"},
                headers={"Accept": "application/json"},
            )
            if r.status_code == 200:
                for entry in r.json():
                    for name in entry.get("name_value", "").split("\n"):
                        name = name.strip().lstrip("*.")
                        if name.endswith(f".{domain}"):
                            sub = name[: -(len(domain) + 1)]
                            if sub and "." not in sub:
                                subs.add(sub)
    except Exception:
        pass
    return list(subs)


def _resolve(sub: str, domain: str) -> dict | None:
    hostname = f"{sub}.{domain}"
    try:
        ip = socket.gethostbyname(hostname)
        return {"hostname": hostname, "ip": ip}
    except socket.gaierror:
        return None


def _get_dns_info(domain: str) -> dict:
    info: dict = {}
    try:
        info["a_record"] = socket.gethostbyname(domain)
    except Exception:
        info["a_record"] = None
    try:
        import dns.resolver  # type: ignore
        for rtype in ("MX", "NS", "TXT"):
            try:
                answers = dns.resolver.resolve(domain, rtype, lifetime=5)
                info[rtype.lower()] = [str(r) for r in answers]
            except Exception:
                info[rtype.lower()] = []
    except ImportError:
        pass
    return info


@cached(ttl=3600)
def scan_domain(domain: str) -> dict:
    domain = domain.lower().strip().lstrip("www.").split("/")[0]
    ct_subs = _crt_sh_subdomains(domain)
    all_subs = list(set(_WORDLIST) | set(ct_subs))

    found: list[dict] = []
    with ThreadPoolExecutor(max_workers=30) as pool:
        futures = {pool.submit(_resolve, sub, domain): sub for sub in all_subs}
        for future in as_completed(futures):
            r = future.result()
            if r:
                found.append(r)

    found.sort(key=lambda x: x["hostname"])
    dns_info = _get_dns_info(domain)

    return {
        "domain": domain,
        "subdomains_found": len(found),
        "subdomains": found,
        "ct_subdomains": len(ct_subs),
        "dns": dns_info,
    }
