"""Company registry search — searches US SEC EDGAR, UK Companies House,
CAC Nigeria, Corporations Canada, Cyprus DRCOR, Singapore ACRA, Estonia's
e-Business Register, Ireland CRO, Brazil Receita Federal, Australia ABN
Lookup, and New Zealand NZBN in parallel.

UK Companies House, Australia ABN Lookup, and New Zealand NZBN require an
API key configured in Settings (each is free to self-register for). All
other sources are free / public, though several (Singapore, Estonia,
Ireland, Brazil) are manual-search-only: their open data is published as
bulk downloads or via APIs this app could not confirm a stable
queryable-by-name endpoint for, so rather than guess and silently return
the wrong thing, they return a direct link to the registry's own search
page instead.
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
    """Search CAC Nigeria company registry via the current front-office
    search API (postapp.cac.gov.ng) — the richer of two CAC endpoints
    confirmed by reading the real source of an open-source npm package
    (`company-verify`) that uses it in production; the previous
    `pre.cac.gov.ng/home/search_name` endpoint only returned
    name/rc_number/status/type, with no address for correlating a hit on
    the map or graph. This endpoint could not be live-tested from this
    app's development sandbox (network egress to postapp.cac.gov.ng is
    blocked there) — verify against a real search after deploying."""
    source = "CAC Nigeria"
    from urllib.parse import urlencode
    manual_url = "https://pre.cac.gov.ng/home/search_name?" + urlencode({"query": name})
    try:
        with get_http_client(timeout=_TIMEOUT) as client:
            r = client.post(
                "https://postapp.cac.gov.ng/postapp/api/front-office/search/company-business-name-it",
                json={"searchTerm": name},
                headers={"User-Agent": _USER_AGENT, "Content-Type": "application/json"},
                follow_redirects=True,
            )
            r.raise_for_status()
            data = r.json()

        if not isinstance(data, dict) or not data.get("success") or not isinstance(data.get("data"), list):
            return {
                "source": source,
                "found": [],
                "error": None,
                "note": "CAC Nigeria returned an unexpected response format. Search manually.",
                "manual_url": manual_url,
            }

        found = []
        for item in data["data"]:
            found.append({
                "name": item.get("approvedName", ""),
                "rc_number": item.get("rcNumber", ""),
                "status": "Active" if item.get("active") else "Inactive",
                "type": item.get("companyTypeName", ""),
                "address": (
                    item.get("address") or item.get("headOfficeAddress")
                    or item.get("branchAddress") or ""
                ),
                "city": item.get("city", ""),
                "state": item.get("state", ""),
                "email": item.get("email") or "",
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


def _search_singapore_acra(_name: str) -> dict:
    """Singapore ACRA (Accounting and Corporate Regulatory Authority)
    entity data is published as open data via data.gov.sg, but this app
    could not confirm a stable, queryable-by-name endpoint for it (the
    dataset's resource id is opaque and data.gov.sg has migrated its API
    surface before) — rather than guess an id that might silently query
    the wrong dataset, this stays manual-search-only, mirroring the
    Cyprus DRCOR entry."""
    return {
        "source": "Singapore — ACRA",
        "found": [],
        "error": None,
        "note": (
            "ACRA company data is open via data.gov.sg, but this app has no "
            "confirmed automated name-search for it yet. Search manually."
        ),
        "manual_url": "https://www.bizfile.gov.sg",
    }


def _search_estonia_business_register(_name: str) -> dict:
    """Estonia's e-Business Register (RIK) opened its data for free in
    2022, but publishes it primarily as bulk downloads rather than a
    confirmed simple name-search API — manual-search-only for the same
    reason as Singapore above."""
    return {
        "source": "Estonia — e-Business Register",
        "found": [],
        "error": None,
        "note": (
            "Estonia's e-Business Register data is open (RIK), but this app "
            "has no confirmed automated name-search for it yet. Search manually."
        ),
        "manual_url": "https://ariregister.rik.ee/eng",
    }


def _search_ireland_cro(_name: str) -> dict:
    """Ireland's CRO launched an Open Data Portal in 2024 (API + daily
    bulk snapshots, CC-BY 4.0), but this app could not confirm a stable
    dataset id for live name search — manual-search-only for now."""
    return {
        "source": "Ireland — CRO",
        "found": [],
        "error": None,
        "note": (
            "CRO company data is open (opendata.cro.ie), but this app has no "
            "confirmed automated name-search for it yet. Search manually."
        ),
        "manual_url": "https://core.cro.ie/search",
    }


def _search_brazil_cnpj(_name: str) -> dict:
    """Brazil's Receita Federal publishes the CNPJ registry only as bulk
    monthly dumps — free re-publications (OpenCNPJ, BrasilAPI) built on
    it generally support lookup by CNPJ number, not by company name, so
    this stays manual-search-only rather than forcing a name-search
    contract onto an API that doesn't offer one."""
    return {
        "source": "Brazil — Receita Federal (CNPJ)",
        "found": [],
        "error": None,
        "note": (
            "Brazil's CNPJ registry is open but is bulk/number-lookup "
            "only, not name search. Search manually."
        ),
        "manual_url": "https://solucoes.receita.fazenda.gov.br/Servicos/cnpjreva/Cnpjreva_Solicitacao.asp",
    }


def _search_australia_abn(name: str, api_key: Optional[str]) -> dict:
    """Search the Australian Business Register (ABN Lookup) by entity
    name. The Business Names Register is open on data.gov.au but this
    app could not confirm a stable resource id for it; instead this uses
    ABR's own JSON web service (`abr.business.gov.au`), which needs a
    free self-registered GUID. Could not be live-tested from this app's
    development sandbox — verify the endpoint/field names after deploying."""
    source = "Australia — ABN Lookup"
    manual_url = "https://abr.business.gov.au/"
    if not api_key:
        return {
            "source": source,
            "found": [],
            "error": None,
            "note": (
                "No ABN Lookup GUID configured. Register a free GUID at "
                "abr.business.gov.au and add it in Settings, or search manually."
            ),
            "manual_url": manual_url,
        }
    try:
        with get_http_client(timeout=_TIMEOUT) as client:
            r = client.get(
                "https://abr.business.gov.au/json/MatchingNames.aspx",
                params={"name": name, "guid": api_key, "maxSearchResults": 10},
                headers={"User-Agent": _USER_AGENT},
                follow_redirects=True,
            )
            r.raise_for_status()
            text = r.text.strip()

        # ABR's JSON endpoint wraps its payload in a JSONP callback by
        # default; strip it defensively in case it always does regardless
        # of any (undocumented) callback param.
        if text.startswith("callback(") and text.endswith(")"):
            text = text[len("callback("):-1]
        import json as _json
        data = _json.loads(text)

        names = data.get("Names") or []
        found = []
        for item in names:
            found.append({
                "name": item.get("Name", ""),
                "abn": item.get("Abn", ""),
                "status": item.get("AbnStatus", ""),
                "type": item.get("NameType", ""),
            })
        return {"source": source, "found": found, "error": None}
    except Exception:
        return {
            "source": source,
            "found": [],
            "error": None,
            "note": (
                "ABN Lookup could not be reached automatically. "
                "Search manually via the link below."
            ),
            "manual_url": manual_url,
        }


def _search_new_zealand_nzbn(name: str, api_key: Optional[str]) -> dict:
    """Search the NZ Business Number (NZBN) register by entity name via
    the Companies Office's public API gateway (api.business.govt.nz),
    which authenticates via a free self-registered subscription key.
    Could not be live-tested from this app's development sandbox —
    verify the endpoint/field names after deploying."""
    source = "New Zealand — NZBN"
    manual_url = "https://www.companiesoffice.govt.nz"
    if not api_key:
        return {
            "source": source,
            "found": [],
            "error": None,
            "note": (
                "No NZBN API key configured. Register a free key at "
                "api.business.govt.nz and add it in Settings, or search manually."
            ),
            "manual_url": manual_url,
        }
    try:
        with get_http_client(timeout=_TIMEOUT) as client:
            r = client.get(
                "https://api.business.govt.nz/gateway/nzbn/v5/entities",
                params={"search-term": name},
                headers={"User-Agent": _USER_AGENT, "Ocp-Apim-Subscription-Key": api_key},
                follow_redirects=True,
            )
            r.raise_for_status()
            data = r.json()

        items = data.get("items") or data.get("Items") or []
        found = []
        for item in items:
            found.append({
                "name": item.get("entityName") or item.get("name", ""),
                "nzbn": item.get("nzbn", ""),
                "status": item.get("entityStatusDescription") or item.get("status", ""),
                "type": item.get("entityTypeDescription") or item.get("type", ""),
            })
        return {"source": source, "found": found, "error": None}
    except Exception:
        return {
            "source": source,
            "found": [],
            "error": None,
            "note": (
                "NZBN API could not be reached automatically. "
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


def _search_duckduckgo_business(name: str) -> dict:
    """Query DuckDuckGo Instant Answer API for business info (free, no key)."""
    source = "DuckDuckGo Instant Answer"
    try:
        with get_http_client(timeout=_TIMEOUT) as client:
            r = client.get(
                "https://api.duckduckgo.com/",
                params={"q": name, "format": "json", "no_redirect": "1", "no_html": "1"},
                headers={"User-Agent": _USER_AGENT},
                follow_redirects=True,
            )
            r.raise_for_status()
            data = r.json()

        info: dict = {}
        abstract = data.get("AbstractText") or ""
        if abstract:
            info["abstract"] = abstract
        if data.get("AbstractURL"):
            info["source_url"] = data["AbstractURL"]

        # Infobox entries (phone, website, email, etc.)
        infobox = data.get("Infobox") or {}
        for entry in infobox.get("content", []):
            label = str(entry.get("label", "")).lower()
            value = str(entry.get("value", "")).strip()
            if not value:
                continue
            if "phone" in label or "telephone" in label:
                info.setdefault("phone", value)
            elif "website" in label or "url" in label or "homepage" in label:
                info.setdefault("website", value)
            elif "email" in label:
                info.setdefault("email", value)
            elif "address" in label or "location" in label:
                info.setdefault("address", value)
            elif "founded" in label or "inception" in label:
                info.setdefault("founded", value)
            elif "employees" in label:
                info.setdefault("employees", value)
            elif "industry" in label or "type" in label:
                info.setdefault("industry", value)

        # RelatedTopics sometimes surface the official site
        if "website" not in info:
            for topic in data.get("RelatedTopics", []):
                first_url = topic.get("FirstURL", "")
                if first_url and "duckduckgo.com" not in first_url:
                    break

        image = data.get("Image") or ""
        if image and not image.startswith("http"):
            image = "https://duckduckgo.com" + image
        if image:
            info["image"] = image

        has_info = bool(abstract or info.get("phone") or info.get("website"))
        return {
            "source": source,
            "found": has_info,
            "info": info,
            "error": None,
        }
    except Exception as exc:
        return {"source": source, "found": False, "info": {}, "error": str(exc)}


def _google_dorks(name: str) -> dict:
    """Generate Google search/dork links for business intelligence (no API needed)."""
    from urllib.parse import quote_plus
    q = quote_plus(name)
    links = [
        {
            "label": "Google Business Search",
            "url": f"https://www.google.com/search?q={q}+business",
            "description": "General Google search for the company name",
        },
        {
            "label": "Google Maps / Places",
            "url": f"https://www.google.com/maps/search/{q}",
            "description": "Find physical address, phone, hours via Google Maps",
        },
        {
            "label": "Contact info dork",
            "url": f'https://www.google.com/search?q="{q}"+(email+OR+phone+OR+contact)',
            "description": "Find publicly listed contact information",
        },
        {
            "label": "LinkedIn company page",
            "url": f"https://www.google.com/search?q=site:linkedin.com+%22{q}%22",
            "description": "Find the official LinkedIn company profile",
        },
        {
            "label": "Official website dork",
            "url": f'https://www.google.com/search?q="{q}"+official+site',
            "description": "Locate the official company website",
        },
        {
            "label": "News articles",
            "url": f"https://news.google.com/search?q={q}",
            "description": "Recent press coverage and news mentions",
        },
    ]
    return {"source": "Google Dorks", "links": links, "error": None}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_companies(name: str, uk_api_key: Optional[str] = None,
                      au_api_key: Optional[str] = None,
                      nz_api_key: Optional[str] = None,
                      progress_cb=None) -> dict:
    """Search company registries in parallel across eleven jurisdictions.

    Args:
        name: Company name to search for.
        uk_api_key: Optional UK Companies House API key (Basic auth username).
        au_api_key: Optional Australia ABN Lookup GUID.
        nz_api_key: Optional New Zealand NZBN API subscription key.
        progress_cb: Optional progress_cb(checked, total) called after each
            registry's search resolves — lets a caller show a live "N of M
            checked" indicator.

    Returns:
        {
            "query": name,
            "results": {
                "us_edgar": {...},
                "uk":       {...},
                "nigeria":  {...},
                "canada":   {...},
                "cyprus":   {...},
                "singapore": {...},
                "estonia":   {...},
                "ireland":   {...},
                "brazil":    {...},
                "australia": {...},
                "new_zealand": {...},
            }
        }
    """
    tasks = {
        "us_edgar":    lambda: _search_us_edgar(name),
        "uk":          lambda: _search_uk_companies_house(name, uk_api_key),
        "nigeria":     lambda: _search_nigeria_cac(name),
        "canada":      lambda: _search_canada_corporations(name),
        "cyprus":      lambda: _search_cyprus_drcor(name),
        "singapore":   lambda: _search_singapore_acra(name),
        "estonia":     lambda: _search_estonia_business_register(name),
        "ireland":     lambda: _search_ireland_cro(name),
        "brazil":      lambda: _search_brazil_cnpj(name),
        "australia":   lambda: _search_australia_abn(name, au_api_key),
        "new_zealand": lambda: _search_new_zealand_nzbn(name, nz_api_key),
        "duckduckgo":  lambda: _search_duckduckgo_business(name),
    }

    results: dict = {}
    total = len(tasks)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {executor.submit(fn): key for key, fn in tasks.items()}
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                results[key] = {
                    "source": key,
                    "found": False,
                    "info": {},
                    "error": f"Unexpected error: {exc}",
                }
            if progress_cb:
                progress_cb(len(results), total)

    # Google dorks are generated locally (no network), add after parallel block
    results["google_dorks"] = _google_dorks(name)

    # Return in a stable key order regardless of completion order
    ordered = {k: results[k] for k in (*tasks, "google_dorks")}
    return {"query": name, "results": ordered}
