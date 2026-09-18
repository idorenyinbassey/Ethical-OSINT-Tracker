"""IMEI service client — imei.info dash API (https://dash.imei.info/api),
with an automatic offline fallback (app.services.tac_lookup) for
manufacturer/model when no paid key is configured, or once its credits
run out. The paid API is the only source for blacklist/stolen/warranty
status; the offline database only ever gives brand/model/checksum
validity, but it never runs out and needs no key."""
import re
from typing import Dict, Any, Optional
from app.repositories.api_config_repository import get_by_service
from app.utils.proxy_config import get_http_client
from app.services import tac_lookup


def fetch_imei(imei: str, timeout: float = 10.0) -> Dict[str, Any]:
    digits = re.sub(r"\D", "", imei or "")
    if not (14 <= len(digits) <= 16):
        return {"error": "Enter a valid IMEI number (14-16 digits)."}

    cfg = get_by_service("IMEIService")
    if cfg and cfg.is_enabled and cfg.api_key and cfg.base_url:
        result = _fetch_paid(digits, cfg, timeout)
        if result is not None:
            return result
        # Paid lookup couldn't be completed (out of credits, connection
        # trouble) — fall back to the free offline database rather than
        # dead-ending the investigation.

    return tac_lookup.lookup_tac(digits)


def _fetch_paid(imei: str, cfg, timeout: float) -> Optional[Dict[str, Any]]:
    """Query the paid imei.info dash API. Returns None (triggering the
    offline fallback) when credits are exhausted or the request fails;
    returns an explicit error dict only for a rejected key, so a broken
    key doesn't silently masquerade as a working offline lookup."""
    base = cfg.base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Accept": "application/json",
    }

    # imei.info dash API endpoints to try in order
    endpoints = [
        f"{base}/imei-detect/{imei}/",
        f"{base}/imei-detect/{imei}",
        f"{base}/imei/{imei}/",
        f"{base}/imei/{imei}",
        f"{base}/check/{imei}/",
    ]

    try:
        with get_http_client(timeout=timeout) as client:
            for url in endpoints:
                try:
                    r = client.get(url, headers=headers)
                    if r.status_code == 200:
                        data = r.json()
                        if data:
                            return data
                    elif r.status_code == 401:
                        return {"error": "IMEI API key rejected (HTTP 401). Check your key in Settings."}
                    elif r.status_code in (402, 403):
                        return None
                except Exception:
                    continue
    except Exception:
        return None

    return None
