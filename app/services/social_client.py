"""Social username search — Sherlock/Maigret approach.

For each site we define:
  - url: profile URL pattern with {username}
  - error_type: "status_code" | "message" | "response_url"
  - error_code: HTTP status that means NOT FOUND (for error_type=status_code)
  - error_msg: substring in body that means NOT FOUND (for error_type=message)
  - error_url: redirect URL that means NOT FOUND (for error_type=response_url)
  - url_probe: optional separate URL to probe (Sherlock urlProbe)
  - error_msg_list: list of strings, any of which means NOT FOUND (Sherlock list errorMsg)
"""
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.utils.proxy_config import get_http_client

# ---------------------------------------------------------------------------
# Sherlock site-list integration
# ---------------------------------------------------------------------------

_SHERLOCK_URL = (
    "https://raw.githubusercontent.com/sherlock-project/sherlock/"
    "master/sherlock_project/resources/data.json"
)
_SHERLOCK_CACHE = Path(__file__).parent.parent / "data" / "sherlock_sites.json"
_SHERLOCK_CACHE_TTL = 86_400  # 24 hours
_sherlock_memory: dict | None = None
_sherlock_loaded_at: float = 0.0


def _load_sherlock_sites() -> dict:
    """Return Sherlock's site dict: in-memory → disk cache → HTTP download."""
    global _sherlock_memory, _sherlock_loaded_at
    now = time.monotonic()
    if _sherlock_memory is not None and (now - _sherlock_loaded_at) < _SHERLOCK_CACHE_TTL:
        return _sherlock_memory

    # Try disk cache first
    if _SHERLOCK_CACHE.exists():
        try:
            age = now - _SHERLOCK_CACHE.stat().st_mtime
            if age < _SHERLOCK_CACHE_TTL:
                data = json.loads(_SHERLOCK_CACHE.read_text("utf-8"))
                _sherlock_memory = data
                _sherlock_loaded_at = now
                return data
        except Exception:
            pass

    # Download fresh copy
    try:
        import httpx
        r = httpx.get(_SHERLOCK_URL, timeout=10, follow_redirects=True)
        if r.status_code == 200:
            data = r.json()
            _SHERLOCK_CACHE.parent.mkdir(parents=True, exist_ok=True)
            _SHERLOCK_CACHE.write_text(json.dumps(data), encoding="utf-8")
            _sherlock_memory = data
            _sherlock_loaded_at = now
            return data
    except Exception:
        pass

    # Fall back to stale disk cache if available
    if _SHERLOCK_CACHE.exists():
        try:
            data = json.loads(_SHERLOCK_CACHE.read_text("utf-8"))
            _sherlock_memory = data
            _sherlock_loaded_at = now
            return data
        except Exception:
            pass

    return {}


def _sherlock_to_defn(entry: dict) -> dict | None:
    """Convert a Sherlock data.json entry to our internal site definition."""
    if not isinstance(entry, dict):
        return None
    if entry.get("isNSFW") or entry.get("disabled"):
        return None
    url = entry.get("url", "")
    if not url:
        return None
    # Sherlock uses {} as placeholder; normalise to {username}
    url = url.replace("{}", "{username}")
    defn: dict = {"url": url}

    error_type = entry.get("errorType", "status_code")
    defn["error_type"] = error_type

    if error_type == "status_code":
        defn["error_code"] = 404

    elif error_type == "message":
        err = entry.get("errorMsg", "")
        if isinstance(err, list):
            defn["error_msg_list"] = [str(m) for m in err]
        else:
            defn["error_msg"] = str(err)

    elif error_type == "response_url":
        defn["error_url"] = str(entry.get("errorUrl", ""))

    url_probe = entry.get("urlProbe")
    if url_probe:
        defn["url_probe"] = url_probe.replace("{}", "{username}")

    return defn


def _get_all_sites() -> dict[str, dict]:
    """Return merged site dict: local SITES take priority over Sherlock entries."""
    merged: dict[str, dict] = dict(SITES)
    sherlock_lower = {k.lower(): k for k in merged}
    for name, entry in _load_sherlock_sites().items():
        if name.lower() in sherlock_lower:
            continue  # our definition takes priority
        defn = _sherlock_to_defn(entry)
        if defn:
            merged[name] = defn
    return merged

_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
_HEADERS = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.5"}

SITES: dict[str, dict] = {
    # ------------------------------------------------------------------ #
    #  ORIGINAL ~36 SITES — DO NOT CHANGE                                #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    #  DEVELOPER / TECHNICAL                                              #
    # ------------------------------------------------------------------ #
    "CodePen": {
        "url": "https://codepen.io/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "CodeSandbox": {
        "url": "https://codesandbox.io/u/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Replit": {
        "url": "https://replit.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "HackerRank": {
        "url": "https://www.hackerrank.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "LeetCode": {
        "url": "https://leetcode.com/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Codeforces": {
        "url": "https://codeforces.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Kaggle": {
        "url": "https://www.kaggle.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "SourceForge": {
        "url": "https://sourceforge.net/u/{username}/profile/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "RubyGems": {
        "url": "https://rubygems.org/profiles/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Packagist": {
        "url": "https://packagist.org/users/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "CratesIO": {
        "url": "https://crates.io/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "HexPm": {
        "url": "https://hex.pm/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Launchpad": {
        "url": "https://launchpad.net/~{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "StackExchange": {
        "url": "https://stackexchange.com/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "CodeChef": {
        "url": "https://www.codechef.com/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Exercism": {
        "url": "https://exercism.org/profiles/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Hackaday": {
        "url": "https://hackaday.io/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "IFTTT": {
        "url": "https://ifttt.com/p/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Glitch": {
        "url": "https://glitch.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Gitea": {
        "url": "https://gitea.io/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Codeberg": {
        "url": "https://codeberg.org/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "AtCoder": {
        "url": "https://atcoder.jp/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "TopCoder": {
        "url": "https://www.topcoder.com/members/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Spoj": {
        "url": "https://www.spoj.com/users/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "GeeksForGeeks": {
        "url": "https://auth.geeksforgeeks.org/user/{username}/practice/",
        "error_type": "status_code",
        "error_code": 404,
    },

    # ------------------------------------------------------------------ #
    #  GAMING                                                             #
    # ------------------------------------------------------------------ #
    "Roblox": {
        "url": "https://www.roblox.com/user.aspx?username={username}",
        "error_type": "message",
        "error_msg": "This user does not exist",
    },
    "NameMC": {
        "url": "https://namemc.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Lichess": {
        "url": "https://lichess.org/@/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "ChessCom": {
        "url": "https://www.chess.com/member/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "ItchIO": {
        "url": "https://itch.io/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "IndieDB": {
        "url": "https://www.indiedb.com/members/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "GOG": {
        "url": "https://www.gog.com/u/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "SpeedrunCom": {
        "url": "https://www.speedrun.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "GameFAQs": {
        "url": "https://gamefaqs.gamespot.com/community/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Kongregate": {
        "url": "https://www.kongregate.com/accounts/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Newgrounds": {
        "url": "https://{username}.newgrounds.com/",
        "error_type": "message",
        "error_msg": "Results not found",
    },
    "PSNProfiles": {
        "url": "https://psnprofiles.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "TrueAchievements": {
        "url": "https://www.trueachievements.com/gamer/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "NintendoLife": {
        "url": "https://www.nintendolife.com/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Overwolf": {
        "url": "https://www.overwolf.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "GamerTag": {
        "url": "https://www.gamertagpicture.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Battlenet": {
        "url": "https://battle.net/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Ubisoft": {
        "url": "https://www.ubisoft.com/en-us/playstats/uplay/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "WarThunder": {
        "url": "https://warthunder.com/en/community/userinfo/id/{username}",
        "error_type": "message",
        "error_msg": "User not found",
    },

    # ------------------------------------------------------------------ #
    #  ART / CREATIVE                                                     #
    # ------------------------------------------------------------------ #
    "ArtStation": {
        "url": "https://www.artstation.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Pixiv": {
        "url": "https://www.pixiv.net/en/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Wattpad": {
        "url": "https://www.wattpad.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Scratch": {
        "url": "https://scratch.mit.edu/users/{username}/",
        "error_type": "message",
        "error_msg": "Scratch - Imagine, Program, Share",
    },
    "500px": {
        "url": "https://500px.com/p/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "VSCO": {
        "url": "https://vsco.co/{username}/gallery",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Unsplash": {
        "url": "https://unsplash.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "EyeEm": {
        "url": "https://www.eyeem.com/u/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Letterboxd": {
        "url": "https://letterboxd.com/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Goodreads": {
        "url": "https://www.goodreads.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "FanfictionNet": {
        "url": "https://www.fanfiction.net/u/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "LiveJournal": {
        "url": "https://{username}.livejournal.com",
        "error_type": "message",
        "error_msg": "Sorry, this content is not available",
    },
    "ArchiveOfOurOwn": {
        "url": "https://archiveofourown.org/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "MyAnimeList": {
        "url": "https://myanimelist.net/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "AniList": {
        "url": "https://anilist.co/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Trakt": {
        "url": "https://trakt.tv/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Redbubble": {
        "url": "https://www.redbubble.com/people/{username}/shop",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Society6": {
        "url": "https://society6.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Zazzle": {
        "url": "https://www.zazzle.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "SmugMug": {
        "url": "https://{username}.smugmug.com/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "ImgBB": {
        "url": "https://imgbb.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },

    # ------------------------------------------------------------------ #
    #  VIDEO / MEDIA / MUSIC                                              #
    # ------------------------------------------------------------------ #
    "Vimeo": {
        "url": "https://vimeo.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Dailymotion": {
        "url": "https://www.dailymotion.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Rumble": {
        "url": "https://rumble.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Odysee": {
        "url": "https://odysee.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Mixcloud": {
        "url": "https://www.mixcloud.com/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Audiomack": {
        "url": "https://audiomack.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "ReverbNation": {
        "url": "https://www.reverbnation.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Bandcamp": {
        "url": "https://{username}.bandcamp.com",
        "error_type": "message",
        "error_msg": "Sorry, that something",
    },
    "LastFm": {
        "url": "https://www.last.fm/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "SoundClick": {
        "url": "https://www.soundclick.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Musixmatch": {
        "url": "https://www.musixmatch.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Genius": {
        "url": "https://genius.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "8tracks": {
        "url": "https://8tracks.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "HypeM": {
        "url": "https://hypem.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Deezer": {
        "url": "https://www.deezer.com/en/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },

    # ------------------------------------------------------------------ #
    #  PROFESSIONAL / BUSINESS                                            #
    # ------------------------------------------------------------------ #
    "Xing": {
        "url": "https://www.xing.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Crunchbase": {
        "url": "https://www.crunchbase.com/person/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Upwork": {
        "url": "https://www.upwork.com/freelancers/~{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "SlideShare": {
        "url": "https://www.slideshare.net/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Scribd": {
        "url": "https://www.scribd.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "ResearchGate": {
        "url": "https://www.researchgate.net/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "AcademiaEdu": {
        "url": "https://independent.academia.edu/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "AboutMe": {
        "url": "https://about.me/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Freelancer": {
        "url": "https://www.freelancer.com/u/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Issuu": {
        "url": "https://issuu.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Guru": {
        "url": "https://www.guru.com/freelancers/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "PeoplePerHour": {
        "url": "https://www.peopleperhour.com/freelancer/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Toptal": {
        "url": "https://www.toptal.com/resume/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Clarity": {
        "url": "https://clarity.fm/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Speaker Deck": {
        "url": "https://speakerdeck.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },

    # ------------------------------------------------------------------ #
    #  SOCIAL / FORUMS                                                    #
    # ------------------------------------------------------------------ #
    "Quora": {
        "url": "https://www.quora.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "AskFm": {
        "url": "https://ask.fm/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "OkRu": {
        "url": "https://ok.ru/{username}",
        "error_type": "message",
        "error_msg": "Invalid page address",
    },
    "Disqus": {
        "url": "https://disqus.com/by/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Minds": {
        "url": "https://www.minds.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Gab": {
        "url": "https://gab.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "MeWe": {
        "url": "https://mewe.com/i/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "TruthSocial": {
        "url": "https://truthsocial.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Gettr": {
        "url": "https://gettr.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Parler": {
        "url": "https://parler.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Diaspora": {
        "url": "https://diaspora.social/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "MySpace": {
        "url": "https://myspace.com/{username}",
        "error_type": "message",
        "error_msg": "page you requested does not exist",
    },
    "Tagged": {
        "url": "https://www.tagged.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Badoo": {
        "url": "https://badoo.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "OkCupid": {
        "url": "https://www.okcupid.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "PlentyOfFish": {
        "url": "https://www.pof.com/viewprofile.aspx?profile_id={username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Zoosk": {
        "url": "https://www.zoosk.com/date/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Amino": {
        "url": "https://aminoapps.com/u/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Plurk": {
        "url": "https://www.plurk.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Mix": {
        "url": "https://mix.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Flipboard": {
        "url": "https://flipboard.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Clubhouse": {
        "url": "https://www.joinclubhouse.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "BeReal": {
        "url": "https://bere.al/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Lemon8": {
        "url": "https://www.lemon8-app.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Bluesky": {
        "url": "https://bsky.app/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Threads": {
        "url": "https://www.threads.net/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Poshmark": {
        "url": "https://poshmark.com/closet/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Depop": {
        "url": "https://www.depop.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Vero": {
        "url": "https://vero.co/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Ello": {
        "url": "https://ello.co/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Metooo": {
        "url": "https://metooo.io/u/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },

    # ------------------------------------------------------------------ #
    #  NIGERIAN & AFRICAN PLATFORMS                                       #
    # ------------------------------------------------------------------ #
    "Nairaland": {
        "url": "https://www.nairaland.com/{username}",
        "error_type": "message",
        "error_msg": "No matching results",
    },
    "Jobberman": {
        "url": "https://www.jobberman.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "AfricanDev": {
        "url": "https://africandev.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Gebeya": {
        "url": "https://gebeya.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },

    # ------------------------------------------------------------------ #
    #  BLOG / WRITING / CONTENT                                          #
    # ------------------------------------------------------------------ #
    "Substack": {
        "url": "https://{username}.substack.com/",
        "error_type": "message",
        "error_msg": "That publication doesn't",
    },
    "Hashnode": {
        "url": "https://hashnode.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "DevTo": {
        "url": "https://dev.to/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "WordPressCom": {
        "url": "https://{username}.wordpress.com/",
        "error_type": "message",
        "error_msg": "doesn't exist",
    },
    "Blogspot": {
        "url": "https://{username}.blogspot.com/",
        "error_type": "message",
        "error_msg": "Blog not found",
    },
    "Ghost": {
        "url": "https://{username}.ghost.io/",
        "error_type": "message",
        "error_msg": "404",
    },
    "Carrd": {
        "url": "https://{username}.carrd.co/",
        "error_type": "message",
        "error_msg": "404",
    },
    "KoFi": {
        "url": "https://ko-fi.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Patreon": {
        "url": "https://www.patreon.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "BuyMeACoffee": {
        "url": "https://www.buymeacoffee.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Linktree": {
        "url": "https://linktr.ee/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Beacons": {
        "url": "https://beacons.ai/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Campsite": {
        "url": "https://campsite.bio/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Taplink": {
        "url": "https://taplink.cc/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Shorby": {
        "url": "https://shorby.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Lnkbio": {
        "url": "https://lnk.bio/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "ContactInBio": {
        "url": "https://contactinbio.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },

    # ------------------------------------------------------------------ #
    #  CRYPTO / NFT / WEB3                                               #
    # ------------------------------------------------------------------ #
    "OpenSea": {
        "url": "https://opensea.io/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Foundation": {
        "url": "https://foundation.app/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Rarible": {
        "url": "https://rarible.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Coinbase": {
        "url": "https://www.coinbase.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Etherscan": {
        "url": "https://etherscan.io/address/{username}",
        "error_type": "message",
        "error_msg": "not found",
    },

    # ------------------------------------------------------------------ #
    #  STREAMING PLATFORMS                                                #
    # ------------------------------------------------------------------ #
    "Kick": {
        "url": "https://kick.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Trovo": {
        "url": "https://trovo.live/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Dlive": {
        "url": "https://dlive.tv/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Caffeine": {
        "url": "https://www.caffeine.tv/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Nimo": {
        "url": "https://www.nimo.tv/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },

    # ------------------------------------------------------------------ #
    #  MISCELLANEOUS / OTHER                                              #
    # ------------------------------------------------------------------ #
    "Wikipedia": {
        "url": "https://en.wikipedia.org/wiki/User:{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Wikia": {
        "url": "https://www.fandom.com/u/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Strava": {
        "url": "https://www.strava.com/athletes/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Garmin": {
        "url": "https://connect.garmin.com/modern/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Peloton": {
        "url": "https://members.onepeloton.com/members/{username}/overview",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Stickee": {
        "url": "https://www.stickee.co/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Etsy": {
        "url": "https://www.etsy.com/people/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "eBay": {
        "url": "https://www.ebay.com/usr/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Airbnb": {
        "url": "https://www.airbnb.com/users/show/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Couchsurfing": {
        "url": "https://www.couchsurfing.com/people/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Ravelry": {
        "url": "https://www.ravelry.com/people/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Instructables": {
        "url": "https://www.instructables.com/member/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "HackerEarth": {
        "url": "https://www.hackerearth.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "CodingGame": {
        "url": "https://www.codingame.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "OSF": {
        "url": "https://osf.io/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Orcid": {
        "url": "https://orcid.org/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Mendeley": {
        "url": "https://www.mendeley.com/profiles/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Zotero": {
        "url": "https://www.zotero.org/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "GitBook": {
        "url": "https://app.gitbook.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Notion": {
        "url": "https://www.notion.so/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "HuggingFace": {
        "url": "https://huggingface.co/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Kaggle Discussions": {
        "url": "https://www.kaggle.com/{username}/discussion",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Shodan": {
        "url": "https://www.shodan.io/member/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "HackTheBox": {
        "url": "https://www.hackthebox.eu/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "TryHackMe": {
        "url": "https://tryhackme.com/p/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "PentesterLab": {
        "url": "https://pentesterlab.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Bugcrowd": {
        "url": "https://bugcrowd.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "HackerOne": {
        "url": "https://hackerone.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Intigriti": {
        "url": "https://app.intigriti.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Synack": {
        "url": "https://www.synack.com/researchers/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Feedly": {
        "url": "https://feedly.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Netlog": {
        "url": "https://netlog.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Coroflot": {
        "url": "https://www.coroflot.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Carbonmade": {
        "url": "https://{username}.carbonmade.com",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Cargo": {
        "url": "https://cargo.site/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Dunked": {
        "url": "https://{username}.dunked.com",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Format": {
        "url": "https://{username}.format.com",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Squarespace": {
        "url": "https://{username}.squarespace.com",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Wix": {
        "url": "https://{username}.wixsite.com",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Contently": {
        "url": "https://{username}.contently.com",
        "error_type": "status_code",
        "error_code": 404,
    },
    "JournalismPortfolio": {
        "url": "https://journoportfolio.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Pressfolios": {
        "url": "https://www.pressfolios.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Muck Rack": {
        "url": "https://muckrack.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Giphy": {
        "url": "https://giphy.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Imgur": {
        "url": "https://imgur.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Gfycat": {
        "url": "https://gfycat.com/@{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Tenor": {
        "url": "https://tenor.com/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Streamable": {
        "url": "https://streamable.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Loom": {
        "url": "https://www.loom.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Anchor": {
        "url": "https://anchor.fm/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Podbean": {
        "url": "https://{username}.podbean.com",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Buzzsprout": {
        "url": "https://www.buzzsprout.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Simplecast": {
        "url": "https://{username}.simplecast.com",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Podomatic": {
        "url": "https://{username}.podomatic.com",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Spreaker": {
        "url": "https://www.spreaker.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Libsyn": {
        "url": "https://{username}.libsyn.com",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Capterra": {
        "url": "https://www.capterra.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "G2": {
        "url": "https://www.g2.com/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Trustpilot": {
        "url": "https://www.trustpilot.com/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Yelp": {
        "url": "https://www.yelp.com/user_details?userid={username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "TripAdvisor": {
        "url": "https://www.tripadvisor.com/Profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Zomato": {
        "url": "https://www.zomato.com/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Untappd": {
        "url": "https://untappd.com/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Vivino": {
        "url": "https://www.vivino.com/users/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Goodfood": {
        "url": "https://www.goodfood.com.au/user/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "AllRecipes": {
        "url": "https://www.allrecipes.com/cook/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "FoodNetwork": {
        "url": "https://www.foodnetwork.com/profiles/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Meetup": {
        "url": "https://www.meetup.com/members/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Eventbrite": {
        "url": "https://www.eventbrite.com/u/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Duolingo": {
        "url": "https://www.duolingo.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Codecademy": {
        "url": "https://www.codecademy.com/profiles/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Khan Academy": {
        "url": "https://www.khanacademy.org/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Coursera": {
        "url": "https://www.coursera.org/user/i/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Udemy": {
        "url": "https://www.udemy.com/user/{username}/",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Skillshare": {
        "url": "https://www.skillshare.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Quizlet": {
        "url": "https://quizlet.com/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Chegg": {
        "url": "https://www.chegg.com/profile/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "ResearcherID": {
        "url": "https://www.researcherid.com/rid/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "ScholarGoogle": {
        "url": "https://scholar.google.com/citations?user={username}",
        "error_type": "status_code",
        "error_code": 404,
    },
    "Semantic Scholar": {
        "url": "https://www.semanticscholar.org/author/{username}",
        "error_type": "status_code",
        "error_code": 404,
    },
}


def _extract_profile_meta(html: str) -> dict:
    """Parse Open Graph and Twitter Card tags to get profile picture, name and bio."""
    meta: dict = {}
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html[:60000], "html.parser")
        for tag in soup.find_all("meta"):
            prop = tag.get("property") or tag.get("name") or ""
            content = (tag.get("content") or "").strip()
            if not content:
                continue
            prop = prop.lower()
            if prop in ("og:title", "twitter:title") and "display_name" not in meta:
                meta["display_name"] = content[:120]
            elif prop in ("og:description", "twitter:description", "description") and "bio" not in meta:
                meta["bio"] = content[:300]
            elif prop in ("og:image", "twitter:image", "twitter:image:src") and "profile_image" not in meta:
                if content.startswith("http"):
                    meta["profile_image"] = content
            elif prop == "og:url" and "canonical_url" not in meta:
                meta["canonical_url"] = content
    except Exception:
        pass
    return meta


def _check_site(name: str, defn: dict, username: str) -> dict:
    url_template = defn["url"]
    url = url_template.replace("{username}", username)

    # Sherlock urlProbe: a separate URL used for the HTTP check
    probe_template = defn.get("url_probe", url_template)
    probe_url = probe_template.replace("{username}", username)

    result = {
        "site": name, "url": url, "found": False,
        "status": "error", "status_code": None, "confidence": "low",
    }

    try:
        with get_http_client(timeout=10) as client:
            r = client.get(probe_url, headers=_HEADERS, follow_redirects=True)
        result["status_code"] = r.status_code

        error_type = defn.get("error_type", "status_code")

        if error_type == "status_code":
            error_code = defn.get("error_code", 404)
            not_found_string = defn.get("not_found_string", "")

            if r.status_code == 200:
                if not_found_string and not_found_string.lower() in r.text[:4000].lower():
                    result["status"] = "not_found"
                else:
                    result["found"] = True
                    result["status"] = "found"
                    final_url = str(r.url).lower()
                    result["confidence"] = "high" if username.lower() in final_url else "low"
            elif r.status_code == error_code:
                result["status"] = "not_found"
            else:
                result["status"] = f"http_{r.status_code}"

        elif error_type == "message":
            error_msg = defn.get("error_msg", "")
            error_msg_list = defn.get("error_msg_list", [])
            if r.status_code == 200:
                body = r.text
                not_found = (
                    (error_msg and error_msg in body) or
                    (error_msg_list and any(m in body for m in error_msg_list))
                )
                if not_found:
                    result["status"] = "not_found"
                else:
                    result["found"] = True
                    result["status"] = "found"
                    result["confidence"] = "high"
            else:
                result["status"] = "not_found"

        elif error_type == "response_url":
            error_url = defn.get("error_url", "")
            if r.status_code == 200 and str(r.url) != error_url:
                result["found"] = True
                result["status"] = "found"
                result["confidence"] = "high"
            else:
                result["status"] = "not_found"

        # For any found result, scrape Open Graph / Twitter Card metadata
        if result["found"]:
            result.update(_extract_profile_meta(r.text))

    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)[:120]

    return result


def search_username(username: str) -> dict:
    """Search for a username across all configured sites (local + Sherlock) concurrently."""
    all_sites = _get_all_sites()
    results = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(_check_site, name, defn, username): name for name, defn in all_sites.items()}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                pass

    results.sort(key=lambda r: r["site"])
    found = [r for r in results if r["found"]]
    confirmed = [r for r in found if r.get("confidence") == "high"]
    return {
        "username": username,
        "found_count": len(found),
        "confirmed_count": len(confirmed),
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
