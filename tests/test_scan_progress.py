"""app.utils.scan_progress + the /investigate/scan-progress/<token> route
and its wiring into Social Search / Company Registry.

The scan itself stays fully synchronous — this is a purely additive side
channel: a progress_cb passed into search_username()/search_companies()
updates an in-memory dict keyed by a client-supplied token, and a small
polling route reads it back. No token means no tracking at all (the
existing behavior, unaffected).
"""
import json
import time
from unittest.mock import patch

from tests.conftest import login
from app.utils import scan_progress
from app.services import social_client, company_client


# ── app.utils.scan_progress ──────────────────────────────────────────────────

def test_make_callback_returns_none_without_a_token():
    assert scan_progress.make_callback(None) is None
    assert scan_progress.make_callback("") is None


def test_make_callback_updates_progress_as_called():
    token = "test-token-1"
    cb = scan_progress.make_callback(token)
    assert scan_progress.get_progress(token) == {"checked": 0, "total": 0}
    cb(3, 10)
    assert scan_progress.get_progress(token) == {"checked": 3, "total": 10}
    cb(10, 10)
    assert scan_progress.get_progress(token) == {"checked": 10, "total": 10}


def test_get_progress_for_unknown_token_returns_zeroes():
    assert scan_progress.get_progress("never-seen-this-token") == {"checked": 0, "total": 0}


def test_stale_entries_are_pruned():
    token = "stale-token"
    scan_progress.make_callback(token)
    assert scan_progress.get_progress(token) == {"checked": 0, "total": 0}
    # Force it stale by rewinding its timestamp past the TTL.
    scan_progress._progress[token]["ts"] = time.time() - scan_progress._TTL_SECONDS - 1
    scan_progress._prune()
    assert token not in scan_progress._progress


# ── search_username() / search_companies() progress_cb wiring ───────────────

def test_search_username_calls_progress_cb_for_each_site(app):
    calls = []
    all_sites = {"A": {"url": "https://a.test/{username}", "error_type": "status_code", "error_code": 404},
                 "B": {"url": "https://b.test/{username}", "error_type": "status_code", "error_code": 404}}
    with patch.object(social_client, "_get_all_sites", return_value=all_sites), \
         patch.object(social_client, "_check_site", return_value={"site": "x", "found": False, "status": "not_found", "status_code": 404, "confidence": "low", "url": ""}):
        result = social_client.search_username("someone", progress_cb=lambda c, t: calls.append((c, t)))

    assert result["total_checked"] == 2
    assert len(calls) == 2
    assert all(t == 2 for _, t in calls)
    assert sorted(c for c, _ in calls) == [1, 2]


def test_search_username_works_without_progress_cb(app):
    all_sites = {"A": {"url": "https://a.test/{username}", "error_type": "status_code", "error_code": 404}}
    with patch.object(social_client, "_get_all_sites", return_value=all_sites), \
         patch.object(social_client, "_check_site", return_value={"site": "A", "found": False, "status": "not_found", "status_code": 404, "confidence": "low", "url": ""}):
        result = social_client.search_username("someone")
    assert result["total_checked"] == 1


def test_search_companies_calls_progress_cb_once_per_registry(app):
    calls = []
    with patch.object(company_client, "get_http_client") as mock_client:
        mock_client.side_effect = Exception("no network in tests")
        result = company_client.search_companies("Acme", progress_cb=lambda c, t: calls.append((c, t)))

    # 11 registries + duckduckgo + google_dorks -> google_dorks runs locally,
    # not through the progress-tracked executor loop.
    assert len(calls) == 12
    assert calls[-1][1] == 12


# ── /investigate/scan-progress/<token> route ────────────────────────────────

def test_scan_progress_route_requires_login(client):
    resp = client.get("/investigate/scan-progress/some-token")
    assert resp.status_code in (302, 401)


def test_scan_progress_route_returns_current_progress(app, client, user_a):
    login(client, user_a.username)
    token = "route-test-token"
    scan_progress.make_callback(token)
    scan_progress._progress[token].update({"checked": 5, "total": 20})

    resp = client.get(f"/investigate/scan-progress/{token}")
    assert resp.status_code == 200
    assert resp.get_json() == {"checked": 5, "total": 20}


def test_scan_progress_route_unknown_token_returns_zeroes(app, client, user_a):
    login(client, user_a.username)
    resp = client.get("/investigate/scan-progress/totally-unknown-token")
    assert resp.get_json() == {"checked": 0, "total": 0}


def test_social_post_with_progress_token_updates_progress(app, client, user_a, case_of_a):
    login(client, user_a.username)
    fake_result = {"username": "bob", "found_count": 0, "confirmed_count": 0, "total_checked": 0, "results": []}

    def fake_search(username, progress_cb=None):
        if progress_cb:
            progress_cb(1, 1)
        return fake_result

    with patch.object(social_client, "search_username", side_effect=fake_search):
        resp = client.post("/investigate/social", data={
            "query": "bob", "case_id": str(case_of_a.id), "progress_token": "social-progress-token",
        })
    assert resp.status_code == 200
    assert scan_progress.get_progress("social-progress-token") == {"checked": 1, "total": 1}
