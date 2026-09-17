"""Domain typosquatting monitor — generates bounded lookalike-domain
permutations of a target domain, DNS-resolves them, and enriches
registered hits with RDAP data. No API key required."""
import logging
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.cache import cached

logger = logging.getLogger(__name__)

_ADJACENT_KEYS = {
    "a": "qsz", "b": "vghn", "c": "xdfv", "d": "serfcx", "e": "wsdr",
    "f": "drtgvc", "g": "ftyhbv", "h": "gyujnb", "i": "ujko", "j": "huikmn",
    "k": "jiolm", "l": "kop", "m": "njk", "n": "bhjm", "o": "iklp",
    "p": "ol", "q": "wa", "r": "edft", "s": "awedxz", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc", "y": "tghu",
    "z": "asx",
}

_HOMOGLYPHS = {
    "o": "0", "l": "1", "i": "1", "e": "3", "a": "4", "s": "5", "g": "9",
}

_COMMON_TLDS = ["net", "org", "co", "io", "info"]


def _split_domain(domain: str) -> tuple[str, str]:
    parts = domain.split(".", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return domain, ""


def _generate_permutations(domain: str) -> list[str]:
    """Generate a bounded, deterministic set of lookalike domains across six
    permutation categories. Capped at 100 and sorted before truncation so
    repeated runs against the same domain always pick the same 100
    candidates (keeps caching/diffing stable).
    """
    name, tld = _split_domain(domain)
    if not name:
        return []

    candidates: set[str] = set()

    # Character omission
    for i in range(len(name)):
        candidates.add(name[:i] + name[i + 1:])

    # Character duplication
    for i in range(len(name)):
        candidates.add(name[:i] + name[i] + name[i:])

    # Adjacent-keyboard substitution
    for i, ch in enumerate(name):
        for adj in _ADJACENT_KEYS.get(ch, ""):
            candidates.add(name[:i] + adj + name[i + 1:])

    # Adjacent-character transposition
    for i in range(len(name) - 1):
        swapped = list(name)
        swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
        candidates.add("".join(swapped))

    # Homoglyph substitution
    for i, ch in enumerate(name):
        if ch in _HOMOGLYPHS:
            candidates.add(name[:i] + _HOMOGLYPHS[ch] + name[i + 1:])

    candidates.discard(name)
    candidates.discard("")

    perms = {f"{c}.{tld}" for c in candidates if c} if tld else set()

    # Common-TLD swap (uses the original, unmodified name)
    if tld:
        for alt_tld in _COMMON_TLDS:
            if alt_tld != tld:
                perms.add(f"{name}.{alt_tld}")

    perms.discard(domain)
    return sorted(perms)[:100]


def _resolve_permutation(perm_domain: str) -> dict | None:
    try:
        ip = socket.gethostbyname(perm_domain)
        return {"domain": perm_domain, "ip": ip}
    except socket.gaierror:
        return None


@cached(ttl=3600)
def scan_typosquats(domain: str) -> dict:
    """Generate lookalike permutations of `domain`, resolve each, and
    enrich registered hits (only) with RDAP registrar/creation data —
    never all candidates, to bound RDAP rate-limit exposure. Never raises.
    """
    domain = domain.lower().strip().removeprefix("www.").split("/")[0]
    try:
        permutations = _generate_permutations(domain)

        registered: list[dict] = []
        if permutations:
            with ThreadPoolExecutor(max_workers=30) as pool:
                futures = {pool.submit(_resolve_permutation, p): p for p in permutations}
                for future in as_completed(futures):
                    hit = future.result()
                    if hit:
                        registered.append(hit)

        registered.sort(key=lambda x: x["domain"])

        from app.services import rdap_client
        for hit in registered:
            try:
                rdap = rdap_client.fetch_domain(hit["domain"])
            except Exception:
                rdap = None
            if rdap:
                hit["registrar"] = rdap.get("registrar")
                hit["created"] = rdap.get("created")
            else:
                hit["registrar"] = None
                hit["created"] = None

        return {
            "domain": domain,
            "permutations_generated": len(permutations),
            "registered_count": len(registered),
            "registered": registered,
            "unregistered_count": len(permutations) - len(registered),
        }
    except Exception:
        logger.exception("Typosquat scan failed for %s", domain)
        return {
            "domain": domain,
            "permutations_generated": 0,
            "registered_count": 0,
            "registered": [],
            "unregistered_count": 0,
        }
