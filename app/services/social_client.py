"""Social username search — Sherlock/Maigret approach.

For each site we define:
  - url: profile URL pattern with {username}
  - error_type: "status_code" | "message" | "response_url"
  - error_code: HTTP status that means NOT FOUND (for error_type=status_code)
  - error_msg: substring in body that means NOT FOUND (for error_type=message)
  - error_url: redirect URL that means NOT FOUND (for error_type=response_url)
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.utils.proxy_config import get_http_client

_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
_HEADERS = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.5"}

SITES: dict[str, dict] = {
    "GitHub": {
        "url": "https://github.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Twitter/X": {
        "url": "https://twitter.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Instagram": {
        "url": "https://www.instagram.com/{username}/",
        "error_type": "message",
        "error_msg": "Sorry, this page isn't available",
    },
    "Reddit": {
        "url": "https://www.reddit.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "LinkedIn": {
        "url": "https://www.linkedin.com/in/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "TikTok": {
        "url": "https://www.tiktok.com/@{username}",
        "error_type": "message",
        "error_msg": "Couldn't find this account",
    },
    "Pinterest": {
        "url": "https://www.pinterest.com/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Telegram": {
        "url": "https://t.me/{username}",
        "error_type": "message",
        "error_msg": "If you have Telegram",
    },
    "YouTube": {
        "url": "https://www.youtube.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Twitch": {
        "url": "https://www.twitch.tv/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Steam": {
        "url": "https://steamcommunity.com/id/{username}",
        "error_type": "message",
        "error_msg": "The specified profile could not be found.",
    },
    "Snapchat": {
        "url": "https://www.snapchat.com/add/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Tumblr": {
        "url": "https://{username}.tumblr.com/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Medium": {
        "url": "https://medium.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "HackerNews": {
        "url": "https://news.ycombinator.com/user?id={username}",
        "error_type": "message",
        "error_msg": "No such user.",
    },
    "GitLab": {
        "url": "https://gitlab.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Bitbucket": {
        "url": "https://bitbucket.org/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Keybase": {
        "url": "https://keybase.io/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "DeviantArt": {
        "url": "https://www.deviantart.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Flickr": {
        "url": "https://www.flickr.com/people/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "VK": {
        "url": "https://vk.com/{username}",
        "error_type": "message",
        "error_msg": "This page no longer exists",
    },
    "Pastebin": {
        "url": "https://pastebin.com/u/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "SoundCloud": {
        "url": "https://soundcloud.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Behance": {
        "url": "https://www.behance.net/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Dribbble": {
        "url": "https://dribbble.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Fiverr": {
        "url": "https://www.fiverr.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "ProductHunt": {
        "url": "https://www.producthunt.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Mastodon": {
        "url": "https://mastodon.social/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "StackOverflow": {
        "url": "https://stackoverflow.com/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Gravatar": {
        "url": "https://en.gravatar.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "DockerHub": {
        "url": "https://hub.docker.com/u/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "NPM": {
        "url": "https://www.npmjs.com/~{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "PyPI": {
        "url": "https://pypi.org/user/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Spotify": {
        "url": "https://open.spotify.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Foursquare": {
        "url": "https://foursquare.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "AngelList": {
        "url": "https://angel.co/u/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
}


def _check_site(name: str, defn: dict, username: str) -> dict:
    url_template = defn["url"]
    if "{username}" in url_template:
        url = url_template.replace("{username}", username)
    else:
        url = url_template.format(username=username)

    result = {"site": name, "url": url, "found": False, "status": "error", "status_code": None}

    try:
        with get_http_client(timeout=10) as client:
            r = client.get(url, headers=_HEADERS, follow_redirects=True)
        result["status_code"] = r.status_code

        error_type = defn.get("error_type", "status_code")

        if error_type == "status_code":
            error_code = defn.get("error_code", 404)
            if r.status_code == 200:
                result["found"] = True
                result["status"] = "found"
            elif r.status_code == error_code:
                result["status"] = "not_found"
            else:
                result["status"] = f"http_{r.status_code}"

        elif error_type == "message":
            error_msg = defn.get("error_msg", "")
            if r.status_code == 200 and error_msg not in r.text:
                result["found"] = True
                result["status"] = "found"
            else:
                result["status"] = "not_found"

        elif error_type == "response_url":
            error_url = defn.get("error_url", "")
            if r.status_code == 200 and str(r.url) != error_url:
                result["found"] = True
                result["status"] = "found"
            else:
                result["status"] = "not_found"

    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)[:120]

    return result


def search_username(username: str) -> dict:
    """Search for a username across all configured sites concurrently."""
    results = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(_check_site, name, defn, username): name for name, defn in SITES.items()}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                pass

    results.sort(key=lambda r: r["site"])
    found = [r for r in results if r["found"]]
    return {
        "username": username,
        "found_count": len(found),
        "total_checked": len(results),
        "results": results,
    }


# Keep backward-compat alias used by existing route
def fetch_social(username: str, **_kwargs) -> list[dict]:
    data = search_username(username)
    out = []
    for r in data["results"]:
        out.append({
            "platform": r["site"],
            "username": username,
            "exists": r["found"],
            "url": r["url"] if r["found"] else "",
            "status": r["status"],
            "status_code": r.get("status_code"),
        })
    return out
