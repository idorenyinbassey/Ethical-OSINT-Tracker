"""Company registry search — searches US SEC EDGAR, UK Companies House,
CAC Nigeria, Corporations Canada, and Cyprus DRCOR in parallel.

UK Companies House requires an API key configured in Settings.
All other sources are free / public.
"""
import httpx
import concurrent.futures
from html.parser import HTMLParser
from typing import Optional
from app.utils.proxy_config import get_http_client


_USER_AGENT = "OSINT-Tracker/1.0 (ethical research)"
_TIMEOUT = 15


# ---------------------------------------------------------------------------
# HTML helper — extracts table rows from Canada Corporations Canada
# ---------------------------------------------------------------------------

class _TableRowParser(HTMLParser):
    """Collect text tokens from <tr> / <td> / <th> elements."""

    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: Optional[list[str]] = None
        self._current_cell: Optional[list[str]] = None
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._current_row = []
        elif tag in ("td", "th") and self._current_row is not None:
            self._current_cell = []
            self._in_cell = True

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._current_cell is not None:
            self._current_row.append(" ".join(self._current_cell).strip())
            self._current_cell = None
            self._in_cell = False
        elif tag == "tr" and self._current_row is not None:
            if any(self._current_row):
                self.rows.append(self._current_row)
            self._current_row = None

    def handle_data(self, data):
        if self._in_cell and self._current_cell is not None:
            text = data.strip()
            if text:
                self._current_cell.append(text)


# ---------------------------------------------------------------------------
# Individual registry fetch functions
# ---------------------------------------------------------------------------

def _search_us_edgar(name: str) -> dict:
    """Search US SEC EDGAR full-text search index (free, no key required)."""
    source = "US SEC EDGAR"
    try:
        url = "https://efts.sec.gov/LATEST/search-index"
        params = {
            "q": f'"{name}"',
            "forms": "10-K,10-Q,S-1",
            "dateRange": "custom",
            "startdt": "2010-01-01",
        }
        with get_http_client(timeout=_TIMEOUT) as client:
            r = client.get(url, params=params, headers={"User-Agent": _USER_AGENT}, follow_redirects=True)
            r.raise_for_status()
            data = r.json()

        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)
        found = []
        for hit in hits:
            src = hit.get("_source", {})
            entity_name = src.get("entity_name") or src.get("display_names", [None])[0] or ""
            form_type = src.get("form_type", "")
            file_date = src.get("file_date", "")
            period = src.get("period_of_report", "")
            found.append({
                "name": entity_name,
                "form": form_type,
                "filed": file_date,
                "period": period,
                "url": (
                    "https://www.sec.gov/cgi-bin/browse-edgar"
                    f"?action=getcompany&company={entity_name}"
                    "&type=10-K&dateb=&owner=include&count=10"
                ),
            })
        return {
            "source": source,
            "found": found,
            "total": total,
            "error": None,
        }
    except Exception as exc:
        return {"source": source, "found": [], "error": str(exc)}


def _search_uk_companies_house(name: str, api_key: Optional[str]) -> dict:
    """Search UK Companies House (requires API key — Basic auth)."""
    source = "UK Companies House"
    if not api_key:
        return {
            "source": source,
            "found": [],
            "error": (
                "No Companies House API key configured. "
                "Add your key in Settings to enable UK company search."
            ),
        }
    try:
        url = "https://api.company-information.service.gov.uk/search/companies"
        params = {"q": name, "items_per_page": 10}
        with get_http_client(timeout=_TIMEOUT) as client:
            r = client.get(
                url,
                params=params,
                headers={"User-Agent": _USER_AGENT},
                auth=(api_key, ""),
                follow_redirects=True,
            )
            r.raise_for_status()
            data = r.json()

        items = data.get("items", [])
        total = data.get("total_results", len(items))
        found = []
        for item in items:
            company_number = item.get("company_number", "")
            address = item.get("address", {})
            address_snippet = ", ".join(
                filter(None, [
                    address.get("premises", ""),
                    address.get("address_line_1", ""),
                    address.get("locality", ""),
                    address.get("postal_code", ""),
                    address.get("country", ""),
                ])
            )
            found.append({
                "name": item.get("title", ""),
                "number": company_number,
                "status": item.get("company_status", ""),
                "type": item.get("company_type", ""),
                "address": address_snippet,
                "url": (
                    f"https://find-and-update.company-information.service.gov.uk"
                    f"/company/{company_number}"
                ),
            })
        return {
            "source": source,
            "found": found,
            "total": total,
            "error": None,
        }
    except Exception as exc:
        return {"source": source, "found": [], "error": str(exc)}


def _search_nigeria_cac(name: str) -> dict:
    """Search CAC Nigeria company registry."""
    source = "CAC Nigeria"
    from urllib.parse import urlencode
    manual_url = "https://pre.cac.gov.ng/home/search_name?" + urlencode({"query": name})
    try:
        with get_http_client(timeout=_TIMEOUT) as client:
            r = client.get(
                "https://pre.cac.gov.ng/home/search_name",
                params={"query": name},
                headers={"User-Agent": _USER_AGENT},
                follow_redirects=True,
            )
            r.raise_for_status()
            data = r.json()

        if not isinstance(data, list):
            return {
                "source": source,
                "found": [],
                "error": None,
                "note": "CAC Nigeria returned an unexpected response format. Search manually.",
                "manual_url": manual_url,
            }

        found = []
        for item in data:
            found.append({
                "name": item.get("company_name", ""),
                "rc_number": item.get("rc_number", ""),
                "status": item.get("status", ""),
                "type": item.get("type", ""),
            })
        return {"source": source, "found": found, "error": None}
    except Exception:
        return {
            "source": source,
            "found": [],
            "error": None,
            "note": (
                "CAC Nigeria portal could not be reached automatically. "
                "Search manually via the link below."
            ),
            "manual_url": manual_url,
        }


def _search_canada_corporations(name: str) -> dict:
    """Search Corporations Canada federal registry via HTML scraping."""
    source = "Corporations Canada"
    try:
        url = "https://ised-isde.canada.ca/cc/lgcy/fdrlCrpSrch.html"
        params = {
            "V_TOKEN": "null",
            "SEARCH_TYPE": "ft",
            "CORPORATION_NAME": name,
        }
        with get_http_client(timeout=_TIMEOUT) as client:
            r = client.get(url, params=params, headers={"User-Agent": _USER_AGENT}, follow_redirects=True)
            r.raise_for_status()
            html = r.text

        parser = _TableRowParser()
        parser.feed(html)

        # Skip header rows; try to detect data rows by looking for rows with
        # at least 3 non-empty cells where the first looks like a company name.
        found = []
        header_skipped = False
        for row in parser.rows:
            cells = [c.strip() for c in row if c.strip()]
            if len(cells) < 2:
                continue
            # Heuristic: skip rows that look like header/label rows
            first = cells[0].lower()
            if not header_skipped and any(
                kw in first for kw in ("corporation", "company", "name", "number", "status")
            ):
                header_skipped = True
                continue
            if len(found) >= 10:
                break
            # Best-effort mapping: name, number, status, url
            entry: dict = {"name": cells[0]}
            if len(cells) >= 2:
                entry["number"] = cells[1]
            if len(cells) >= 3:
                entry["status"] = cells[2]
            entry["url"] = str(r.url)
            found.append(entry)

        return {"source": source, "found": found, "error": None}
    except Exception as exc:
        return {"source": source, "found": [], "error": str(exc)}


def _search_cyprus_drcor(_name: str) -> dict:
    """Cyprus DRCOR — portal requires browser login; return manual referral."""
    return {
        "source": "Cyprus — DRCOR",
        "found": [],
        "error": None,
        "note": "Cyprus requires the DRCOR eFiling portal.",
        "manual_url": (
            "https://efiling.drcor.mcit.gov.cy/DrcorPublicSite/BusinessSearch.aspx"
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_companies(name: str, uk_api_key: Optional[str] = None) -> dict:
    """Search company registries in parallel across five jurisdictions.

    Args:
        name: Company name to search for.
        uk_api_key: Optional UK Companies House API key (Basic auth username).

    Returns:
        {
            "query": name,
            "results": {
                "us_edgar": {...},
                "uk":       {...},
                "nigeria":  {...},
                "canada":   {...},
                "cyprus":   {...},
            }
        }
    """
    tasks = {
        "us_edgar": lambda: _search_us_edgar(name),
        "uk":       lambda: _search_uk_companies_house(name, uk_api_key),
        "nigeria":  lambda: _search_nigeria_cac(name),
        "canada":   lambda: _search_canada_corporations(name),
        "cyprus":   lambda: _search_cyprus_drcor(name),
    }

    results: dict = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fn): key for key, fn in tasks.items()}
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                results[key] = {
                    "source": key,
                    "found": [],
                    "error": f"Unexpected error: {exc}",
                }

    # Return in a stable key order regardless of completion order
    ordered = {k: results[k] for k in tasks}
    return {"query": name, "results": ordered}
