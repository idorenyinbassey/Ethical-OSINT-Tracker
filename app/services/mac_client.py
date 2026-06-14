"""MAC address vendor lookup using macvendors.com (free, no API key)."""
import re
from app.services.cache import cached
from app.utils.proxy_config import get_http_client


def _normalise(mac: str) -> str:
    """Strip separators and uppercase."""
    return re.sub(r"[:\-\.]", "", mac).upper()


@cached(ttl=86400)
def lookup_mac(mac: str) -> dict:
    clean = _normalise(mac)
    if len(clean) < 6 or not re.match(r"^[0-9A-F]+$", clean):
        return {"error": "Invalid MAC address. Expected format: AA:BB:CC:DD:EE:FF"}

    formatted = ":".join(clean[i : i + 2] for i in range(0, 12, 2)) if len(clean) >= 12 else ":".join(clean[i : i + 2] for i in range(0, len(clean), 2))
    oui = ":".join(clean[i : i + 2] for i in range(0, 6, 2))

    try:
        with get_http_client(timeout=8) as client:
            r = client.get(
                f"https://api.macvendors.com/{formatted}",
                headers={"Accept": "text/plain"},
            )
        if r.status_code == 200:
            return {"mac_address": formatted, "oui": oui, "vendor": r.text.strip()}
        if r.status_code == 404:
            return {"mac_address": formatted, "oui": oui, "vendor": "Unknown — OUI not in database"}
        return {"mac_address": formatted, "oui": oui, "error": f"HTTP {r.status_code}"}
    except Exception as exc:
        return {"mac_address": formatted, "oui": oui, "error": str(exc)}
