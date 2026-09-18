"""app.utils.scraper_health — canary checks for the app's web-scraping-based
data sources (AHMIA, Sherlock's site list, Company Registry's Canada
scraper). run_canaries() must never raise even if a check's underlying
service call blows up, and check_and_notify() must send exactly one
summary notification when any check fails, via the same
notification_service.notify() used for watchlist alerts."""
from unittest.mock import patch
from app.utils import scraper_health


def test_run_canaries_reports_success_for_all_passing_checks():
    fake_checks = [
        ("Dark Web Search (Ahmia)", lambda: (True, "5 result(s)")),
        ("Social Search (Sherlock site list)", lambda: (True, "616 site(s) loaded")),
        ("Company Registry (Canada)", lambda: (True, "1 result(s)")),
    ]
    with patch.object(scraper_health, "_CHECKS", fake_checks):
        results = scraper_health.run_canaries()

    assert len(results) == 3
    assert all(r["ok"] for r in results)


def test_run_canaries_reports_failure_without_raising():
    def _boom():
        raise RuntimeError("network unreachable")

    with patch.object(scraper_health, "_CHECKS", [("Fake Check", _boom)]):
        results = scraper_health.run_canaries()

    assert len(results) == 1
    assert results[0]["ok"] is False
    assert "network unreachable" in results[0]["detail"]


def test_run_canaries_reports_false_result_from_a_check():
    with patch.object(scraper_health, "_CHECKS", [("Fake Check", lambda: (False, "0 result(s)"))]):
        results = scraper_health.run_canaries()

    assert results == [{"name": "Fake Check", "ok": False, "detail": "0 result(s)"}]


def test_check_and_notify_sends_one_notification_on_failure():
    with patch.object(scraper_health, "_CHECKS", [("Fake Check", lambda: (False, "0 result(s)"))]), \
         patch("app.services.notification_service.notify") as mock_notify:
        scraper_health.check_and_notify()

    mock_notify.assert_called_once()
    _, kwargs = mock_notify.call_args
    assert "Fake Check" in kwargs["body"]


def test_check_and_notify_sends_nothing_when_all_pass():
    with patch.object(scraper_health, "_CHECKS", [("Fake Check", lambda: (True, "ok"))]), \
         patch("app.services.notification_service.notify") as mock_notify:
        scraper_health.check_and_notify()

    mock_notify.assert_not_called()


def test_check_and_notify_never_raises_if_notify_itself_fails():
    with patch.object(scraper_health, "_CHECKS", [("Fake Check", lambda: (False, "0 result(s)"))]), \
         patch("app.services.notification_service.notify", side_effect=Exception("webhook down")):
        results = scraper_health.check_and_notify()

    assert results[0]["ok"] is False


def test_check_darkweb_fails_on_zero_results():
    with patch("app.services.darkweb_client.search_ahmia", return_value={"total": 0, "results": []}):
        ok, detail = scraper_health._check_darkweb()
    assert ok is False
    assert "0" in detail


def test_check_darkweb_passes_on_results():
    with patch("app.services.darkweb_client.search_ahmia", return_value={"total": 3, "results": [1, 2, 3]}):
        ok, detail = scraper_health._check_darkweb()
    assert ok is True


def test_check_darkweb_fails_on_error_key():
    with patch("app.services.darkweb_client.search_ahmia",
               return_value={"error": "timed out", "error_type": "timeout", "results": []}):
        ok, detail = scraper_health._check_darkweb()
    assert ok is False
    assert "timed out" in detail


class _FakeSherlockResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data


class _FakeSherlockClient:
    def __init__(self, response):
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, **kwargs):
        return self._response


def _sherlock_client_factory(response):
    def factory(timeout=10):
        return _FakeSherlockClient(response)
    return factory


def test_check_sherlock_sites_fails_below_floor():
    response = _FakeSherlockResponse({str(i): {} for i in range(2)})
    with patch("app.utils.proxy_config.get_http_client", _sherlock_client_factory(response)):
        ok, detail = scraper_health._check_sherlock_sites()
    assert ok is False


def test_check_sherlock_sites_passes_above_floor():
    response = _FakeSherlockResponse({str(i): {} for i in range(150)})
    with patch("app.utils.proxy_config.get_http_client", _sherlock_client_factory(response)):
        ok, detail = scraper_health._check_sherlock_sites()
    assert ok is True


def test_check_sherlock_sites_fails_on_non_200():
    response = _FakeSherlockResponse({}, status_code=503)
    with patch("app.utils.proxy_config.get_http_client", _sherlock_client_factory(response)):
        ok, detail = scraper_health._check_sherlock_sites()
    assert ok is False
    assert "503" in detail


def test_check_sherlock_sites_does_not_use_the_local_cache():
    # A stale-but-large local cache must not mask a broken live fetch —
    # this canary bypasses social_client's cache entirely.
    with patch("app.services.social_client._load_sherlock_sites",
               return_value={str(i): {} for i in range(1000)}), \
         patch("app.utils.proxy_config.get_http_client",
               _sherlock_client_factory(_FakeSherlockResponse({}, status_code=500))):
        ok, detail = scraper_health._check_sherlock_sites()
    assert ok is False


def test_check_company_registry_canada_fails_on_no_results():
    with patch("app.services.company_client._search_canada_corporations",
               return_value={"source": "Corporations Canada", "found": [], "error": None}):
        ok, detail = scraper_health._check_company_registry_canada()
    assert ok is False


def test_check_company_registry_canada_passes_on_results():
    with patch("app.services.company_client._search_canada_corporations",
               return_value={"source": "Corporations Canada", "found": [{"name": "Royal Bank Of Canada"}], "error": None}):
        ok, detail = scraper_health._check_company_registry_canada()
    assert ok is True
