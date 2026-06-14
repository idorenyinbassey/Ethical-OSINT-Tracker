import httpx
from urllib.parse import urlparse
from app.repositories.api_config_repository import get_by_service

_ALLOWED_SCHEMES = {"socks5", "socks5h", "socks4", "http", "https"}


def get_proxy_url() -> str | None:
    """Return proxy URL if TorProxy is configured, enabled, and has a valid scheme."""
    try:
        cfg = get_by_service("TorProxy")
        if cfg and cfg.is_enabled and cfg.base_url:
            parsed = urlparse(cfg.base_url)
            if parsed.scheme in _ALLOWED_SCHEMES and parsed.hostname:
                return cfg.base_url
    except Exception:
        pass
    return None


def get_http_client(timeout: int = 8) -> httpx.Client:
    """Return an httpx.Client, optionally routed through Tor or a proxy."""
    proxy = get_proxy_url()
    if proxy:
        return httpx.Client(proxy=proxy, timeout=timeout)
    return httpx.Client(timeout=timeout)
