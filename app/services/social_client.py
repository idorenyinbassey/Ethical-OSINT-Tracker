"""Lightweight social search client — sync version using ThreadPoolExecutor."""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

import httpx

from app.repositories.api_config_repository import get_by_service
from app.utils.rate_limiter import RateLimiter

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


def _probe(url: str, timeout: float) -> int:
    headers = {"User-Agent": "Ethical-OSINT-Tracker/1.0"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.head(url, headers=headers)
            return r.status_code
    except Exception:
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                r = client.get(url, headers=headers)
                return r.status_code
        except Exception:
            return 0


def _parse_api_keys(config_notes: Optional[str]) -> dict:
    if not config_notes:
        return {}
    try:
        keys = json.loads(config_notes)
        if isinstance(keys, dict):
            return keys
    except (json.JSONDecodeError, TypeError):
        pass
    return {}


def _check_github_api(username: str, api_key: str, timeout: float) -> dict:
    rate_limiter = RateLimiter(key=f"social:github:{username}", max_calls=5000, period=3600)
    if not rate_limiter.allow():
        return {"platform": "GitHub", "username": username, "exists": False, "url": "", "error": "Rate limit exceeded"}
    try:
        with httpx.Client(timeout=timeout) as client:
            headers = {"Authorization": f"token {api_key}", "Accept": "application/vnd.github.v3+json"}
            r = client.get(f"https://api.github.com/users/{username}", headers=headers)
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
                    },
                }
    except Exception:
        pass
    return {"platform": "GitHub", "username": username, "exists": False, "url": ""}


def _check_twitter_api(username: str, bearer_token: str, timeout: float) -> dict:
    rate_limiter = RateLimiter(key=f"social:twitter:{username}", max_calls=300, period=900)
    if not rate_limiter.allow():
        return {"platform": "Twitter", "username": username, "exists": False, "url": "", "error": "Rate limit exceeded"}
    try:
        with httpx.Client(timeout=timeout) as client:
            headers = {"Authorization": f"Bearer {bearer_token}"}
            r = client.get(
                f"https://api.twitter.com/2/users/by/username/{username}",
                headers=headers,
                params={"user.fields": "description,location,public_metrics"},
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
                    },
                }
    except Exception:
        pass
    return {"platform": "Twitter", "username": username, "exists": False, "url": ""}


def _check_platform(platform: str, username: str, api_keys: dict, timeout: float) -> dict:
    if platform == "GitHub" and api_keys.get("github"):
        return _check_github_api(username, api_keys["github"], timeout)
    if platform == "Twitter" and api_keys.get("twitter"):
        return _check_twitter_api(username, api_keys["twitter"], timeout)

    pattern = PLATFORM_URLS.get(platform)
    if not pattern:
        return {"platform": platform, "username": username, "exists": False, "url": ""}

    url = pattern.format(username=username)
    status = _probe(url, timeout)
    exists = status == 200
    return {"platform": platform, "username": username, "exists": exists, "url": url if exists else ""}


def fetch_social(username: str, platforms: List[str] | None = None, timeout: float = 5.0) -> List[dict]:
    """Check for public profiles across platforms using a thread pool."""
    if platforms is None:
        platforms = list(PLATFORM_URLS.keys())

    config = get_by_service("SocialSearch")
    api_keys = _parse_api_keys(config.notes if config else None)

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_check_platform, p, username, api_keys, timeout): p
            for p in platforms
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                p = futures[future]
                results.append({"platform": p, "username": username, "exists": False, "url": ""})

    results.sort(key=lambda x: x["platform"])
    return results
