"""Person / full-name OSINT helper — generates investigation links and username guesses.

No data is sent to third parties; only clickable URL templates are produced.
"""
from urllib.parse import quote_plus
from typing import List


def _generate_dorks(name: str) -> List[dict]:
    """Return a list of dork-link dicts for the given full name.

    Each dict has keys: label, url, description.
    """
    q = quote_plus(f'"{name}"')          # "John Doe" encoded
    q_plain = quote_plus(name)            # John+Doe encoded (no quotes)

    dorks = [
        {
            "label": "Google — General",
            "url": f'https://www.google.com/search?q={q}',
            "description": "Broad web search for the exact name.",
        },
        {
            "label": "Google — LinkedIn",
            "url": f'https://www.google.com/search?q=site%3Alinkedin.com%2Fin+{q}',
            "description": "LinkedIn profile pages mentioning this name.",
        },
        {
            "label": "Google — News",
            "url": f'https://www.google.com/search?q={q}&tbm=nws',
            "description": "News articles referencing this name.",
        },
        {
            "label": "Google — Images",
            "url": f'https://www.google.com/search?q={q}&tbm=isch',
            "description": "Images associated with this name.",
        },
        {
            "label": "Google — Facebook",
            "url": f'https://www.google.com/search?q=site%3Afacebook.com+{q}',
            "description": "Facebook pages and profiles for this name.",
        },
        {
            "label": "Google — Court Records",
            "url": f'https://www.google.com/search?q={q}+%22court%22+OR+%22lawsuit%22',
            "description": "Search for court filings or lawsuits mentioning this name.",
        },
        {
            "label": "Bing — General",
            "url": f'https://www.bing.com/search?q={q}',
            "description": "Bing web search — may surface results Google misses.",
        },
        {
            "label": "Nairaland",
            "url": f'https://www.nairaland.com/search?q={q_plain}&board=0',
            "description": "Nigerian online community forum search.",
        },
        {
            "label": "PeopleFinder",
            "url": f'https://www.peoplefinder.com/search/?q={q_plain}',
            "description": "US people-finder directory.",
        },
        {
            "label": "SEC EDGAR — Officers",
            "url": f'https://efts.sec.gov/LATEST/search-index?q={q}&dateRange=custom&startdt=2000-01-01',
            "description": "SEC filings mentioning this person as a company officer.",
        },
        {
            "label": "Google Scholar",
            "url": f'https://scholar.google.com/scholar?q={q}',
            "description": "Academic papers and citations.",
        },
        {
            "label": "Twitter / X",
            "url": f'https://twitter.com/search?q={q}',
            "description": "Tweets mentioning or by this name.",
        },
    ]
    return dorks


def _username_guesses(name: str) -> List[str]:
    """Generate up to 8 likely social-media username variants from a full name."""
    parts = name.lower().split()
    if len(parts) < 2:
        # Single name — return just that token and a few minor variants.
        token = parts[0] if parts else name.lower()
        return [token, token + "1", token + "_", token + "99"]

    first = parts[0]
    last = parts[-1]
    f = first[0]
    l = last[0]  # noqa: E741

    candidates = [
        first + last,          # johndoe
        first + "." + last,   # john.doe
        first + "_" + last,   # john_doe
        f + last,              # jdoe
        last + first,          # doejohn
        last + f,              # doej
        first + l,             # johnd
        first,                 # john
    ]

    # Deduplicate while preserving order, cap at 8.
    seen: set = set()
    result: List[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            result.append(c)
        if len(result) == 8:
            break
    return result


def search_person(name: str) -> dict:
    """Generate OSINT investigation links and username guesses for a full name.

    No HTTP requests are made — all outputs are clickable URLs for the analyst
    to open manually.

    Returns:
        {
            "name": str,
            "dork_links": [{"label": str, "url": str, "description": str}, ...],
            "username_guesses": [str, ...],
            "note": str,
        }
    """
    name = name.strip()
    return {
        "name": name,
        "dork_links": _generate_dorks(name),
        "username_guesses": _username_guesses(name),
        "note": (
            "Open the links to investigate. "
            "Use username guesses with the Social Search tool."
        ),
    }
