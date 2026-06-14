import httpx
from app.repositories.api_config_repository import get_by_service


def get_proxy_url() -> str | None:
    """Return SOCKS5/HTTP proxy URL if TorProxy service is configured and enabled."""
    try:
        cfg = get_by_service("TorProxy")
        if cfg and cfg.is_enabled and cfg.base_url:
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
