"""Subdomain and DNS scanner — uses crt.sh (Certificate Transparency) + DNS resolution wordlist."""
import logging
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.cache import cached
from app.utils.proxy_config import get_http_client

logger = logging.getLogger(__name__)

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
        logger.exception("crt.sh subdomain lookup failed for %s", domain)
    return list(subs)


def _resolve(sub: str, domain: str) -> dict | None:
    hostname = f"{sub}.{domain}"
    try:
        ip = socket.gethostbyname(hostname)
        return {"hostname": hostname, "ip": ip}
    except socket.gaierror:
        return None


def _probe_http(hostname: str) -> dict | None:
    """Probe a resolved subdomain over HTTP(S) — status, final URL (after
    redirects), server header, and page title. Tries HTTPS first, falling
    back to HTTP only on a connection-level failure (not on a non-2xx
    response, which is still a valid probe result). Returns None if
    neither scheme responds — never raises, matching `_resolve`'s
    "return None on failure" convention so a bad host never poisons the
    ThreadPoolExecutor pass.
    """
    for scheme in ("https", "http"):
        try:
            with get_http_client(timeout=6) as client:
                r = client.get(f"{scheme}://{hostname}", follow_redirects=True)
            title = None
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text[:20000], "html.parser")
                if soup.title and soup.title.string:
                    title = soup.title.string.strip()[:200]
            except Exception:
                pass
            return {
                "scheme": scheme,
                "status_code": r.status_code,
                "final_url": str(r.url),
                "server": r.headers.get("server", ""),
                "title": title,
            }
        except Exception:
            continue  # try the next scheme, or fall through to None
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
    domain = domain.lower().strip().removeprefix("www.").split("/")[0]
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

    # Second pass: probe HTTP(S) on resolved hosts only. Lower concurrency
    # than the DNS pass above (20 vs 30) — HTTP requests are heavier, and
    # this app scans only domains the user is authorised to test, so
    # bounding request volume against target infrastructure is a
    # deliberate ethical-scanning choice, not just a performance one.
    http_probed_count = 0
    if found:
        with ThreadPoolExecutor(max_workers=20) as pool:
            probe_futures = {pool.submit(_probe_http, item["hostname"]): item for item in found}
            for future in as_completed(probe_futures):
                item = probe_futures[future]
                probe = future.result()
                item["http"] = probe
                if probe is not None:
                    http_probed_count += 1

    dns_info = _get_dns_info(domain)

    return {
        "domain": domain,
        "subdomains_found": len(found),
        "subdomains": found,
        "ct_subdomains": len(ct_subs),
        "http_probed_count": http_probed_count,
        "dns": dns_info,
    }
