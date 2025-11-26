"""Lightweight social search client with API integration.

This client checks public profile URLs across a configurable list of
platforms. When API keys are configured in SocialSearch settings, it uses
authenticated API calls for richer data. Falls back to HTTP HEAD checks
when API keys are not provided.

Note: Respect site ToS when enabling large-scale checks. This client is
intended for light, manual use within the app and should be configured
with proper rate limits in production.
"""
import asyncio
import json
from typing import List, Optional

import httpx

from app.repositories.api_config_repository import get_by_service
from app.utils.rate_limiter import RateLimiter

# Default platforms and their public profile URL patterns. Patterns
# should include a single `{username}` placeholder.
PLATFORM_URLS = {
    "Twitter": "https://twitter.com/{username}",
    "GitHub": "https://github.com/{username}",
    "Instagram": "https://www.instagram.com/{username}/",
    "Reddit": "https://www.reddit.com/user/{username}",
    "LinkedIn": "https://www.linkedin.com/in/{username}",
    "Pinterest": "https://www.pinterest.com/{username}/",
    "TikTok": "https://www.tiktok.com/@{username}",
    "Telegram": "https://t.me/{username}",
    "Facebook": "https://www.facebook.com/{username}",
    "YouTube": "https://www.youtube.com/c/{username}",
}


async def _probe(client: httpx.AsyncClient, url: str, timeout: float) -> int:
    try:
        # Use HEAD where possible to reduce payload; fall back to GET
        r = await client.head(url, timeout=timeout, follow_redirects=True)
        return r.status_code
    except (httpx.HTTPError, httpx.ReadTimeout):
        try:
            r = await client.get(url, timeout=timeout, follow_redirects=True)
            return r.status_code
        except Exception:
            return 0


def _parse_api_keys(config_notes: Optional[str]) -> dict:
    """Parse JSON API keys from SocialSearch config notes field."""
    if not config_notes:
        return {}
    try:
        keys = json.loads(config_notes)
        if isinstance(keys, dict):
            return keys
    except (json.JSONDecodeError, TypeError):
        pass
    return {}


async def _check_github_api(username: str, api_key: str, timeout: float) -> dict:
    """Check GitHub user via authenticated API call."""
    rate_limiter = RateLimiter(key=f"social:github:{username}", max_calls=5000, period=3600)
    if not rate_limiter.allow():
        return {"platform": "GitHub", "username": username, "exists": False, "url": "", "error": "Rate limit exceeded"}
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            headers = {"Authorization": f"token {api_key}", "Accept": "application/vnd.github.v3+json"}
            r = await client.get(f"https://api.github.com/users/{username}", headers=headers)
            if r.status_code == 200:
                data = r.json()
                return {
                    "platform": "GitHub",
                    "username": username,
                    "exists": True,
                    "url": data.get("html_url", f"https://github.com/{username}"),
                    "profile_data": {
                        "name": data.get("name"),
                        "bio": data.get("bio"),
                        "location": data.get("location"),
                        "public_repos": data.get("public_repos"),
                        "followers": data.get("followers"),
                    }
                }
    except Exception:
        pass
    return {"platform": "GitHub", "username": username, "exists": False, "url": ""}


async def _check_twitter_api(username: str, bearer_token: str, timeout: float) -> dict:
    """Check Twitter user via authenticated API v2 call."""
    rate_limiter = RateLimiter(key=f"social:twitter:{username}", max_calls=300, period=900)  # 300/15min
    if not rate_limiter.allow():
        return {"platform": "Twitter", "username": username, "exists": False, "url": "", "error": "Rate limit exceeded"}
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            headers = {"Authorization": f"Bearer {bearer_token}"}
            r = await client.get(
                f"https://api.twitter.com/2/users/by/username/{username}",
                headers=headers,
                params={"user.fields": "description,location,public_metrics"}
            )
            if r.status_code == 200:
                data = r.json().get("data", {})
                return {
                    "platform": "Twitter",
                    "username": username,
                    "exists": True,
                    "url": f"https://twitter.com/{username}",
                    "profile_data": {
                        "name": data.get("name"),
                        "description": data.get("description"),
                        "location": data.get("location"),
                        "followers": data.get("public_metrics", {}).get("followers_count"),
                    }
                }
    except Exception:
        pass
    return {"platform": "Twitter", "username": username, "exists": False, "url": ""}


async def fetch_social(username: str, platforms: List[str] | None = None, timeout: float = 5.0) -> List[dict]:
    """Check for public profiles across a set of platforms.

    Uses authenticated API calls when API keys are configured in SocialSearch settings.
    Falls back to HTTP HEAD checks when API keys not provided.

    Args:
        username: The username to look for.
        platforms: Optional list of platform keys from PLATFORM_URLS to check.
        timeout: Per-request timeout in seconds.

    Returns:
        A list of dicts: {platform, username, exists(bool), url, profile_data(optional)}
    """
    if platforms is None:
        platforms = list(PLATFORM_URLS.keys())

    # Get API keys from config
    config = get_by_service("SocialSearch")
    api_keys = _parse_api_keys(config.notes if config else None)

    headers = {
        "User-Agent": "Ethical-OSINT-Tracker/1.0 (+https://github.com/idorenyinbassey)"
    }
    results = []
    
    for p in platforms:
        # Try authenticated API calls first
        if p == "GitHub" and api_keys.get("github"):
            result = await _check_github_api(username, api_keys["github"], timeout)
            results.append(result)
            await asyncio.sleep(0.5)
            continue
        
        if p == "Twitter" and api_keys.get("twitter"):
            result = await _check_twitter_api(username, api_keys["twitter"], timeout)
            results.append(result)
            await asyncio.sleep(0.5)
            continue
        
        # Fallback to HTTP HEAD check
        pattern = PLATFORM_URLS.get(p)
        if not pattern:
            continue
        
        url = pattern.format(username=username)
        async with httpx.AsyncClient(headers=headers) as client:
            status = await _probe(client, url, timeout)
            exists = status == 200
            results.append({"platform": p, "username": username, "exists": exists, "url": url if exists else ""})
        
        # Gentle pacing to avoid hammering services
        await asyncio.sleep(0.2)

    return results
