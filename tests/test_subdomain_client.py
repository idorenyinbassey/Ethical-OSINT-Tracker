"""app.services.subdomain_client — passive (crt.sh) + brute-force subdomain
discovery, plus HTTP probing and (this phase) takeover detection of
resolved hosts."""
import dns.resolver
from unittest.mock import patch, MagicMock
from app.services import subdomain_client


class _FakeResponse:
    def __init__(self, status_code=200, text="", headers=None, url="https://x"):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self.url = url


class _FakeClient:
    """Fake get_http_client() context manager."""
    def __init__(self, get_impl):
        self._get_impl = get_impl

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, **kwargs):
        return self._get_impl(url, **kwargs)


def _client_factory(get_impl):
    def factory(timeout=8):
        return _FakeClient(get_impl)
    return factory


def test_probe_http_success_with_title():
    html = "<html><head><title>Hello World</title></head><body></body></html>"

    def get_impl(url, **kwargs):
        assert url.startswith("https://")
        return _FakeResponse(status_code=200, text=html, headers={"server": "nginx"},
                              url="https://sub.example.com/")

    with patch.object(subdomain_client, "get_http_client", _client_factory(get_impl)):
        result = subdomain_client._probe_http("sub.example.com")

    assert result is not None
    assert result["status_code"] == 200
    assert result["scheme"] == "https"
    assert result["server"] == "nginx"
    assert result["title"] == "Hello World"


def test_probe_http_falls_back_to_http_on_https_failure():
    calls = []

    def get_impl(url, **kwargs):
        calls.append(url)
        if url.startswith("https://"):
            raise Exception("connection refused")
        return _FakeResponse(status_code=200, text="<title>ok</title>")

    with patch.object(subdomain_client, "get_http_client", _client_factory(get_impl)):
        result = subdomain_client._probe_http("sub.example.com")

    assert result is not None
    assert result["scheme"] == "http"
    assert calls[0].startswith("https://")
    assert calls[1].startswith("http://")


def test_probe_http_both_schemes_fail_returns_none():
    def get_impl(url, **kwargs):
        raise Exception("timed out")

    with patch.object(subdomain_client, "get_http_client", _client_factory(get_impl)):
        result = subdomain_client._probe_http("sub.example.com")

    assert result is None


def test_probe_http_no_title_tag_is_none():
    def get_impl(url, **kwargs):
        return _FakeResponse(status_code=404, text="<html><body>not found</body></html>")

    with patch.object(subdomain_client, "get_http_client", _client_factory(get_impl)):
        result = subdomain_client._probe_http("sub.example.com")

    assert result is not None
    assert result["status_code"] == 404
    assert result["title"] is None


def test_scan_domain_probes_resolved_hosts_and_counts_them():
    # scan_domain is @cached — use a domain unique to this test so it
    # can't return another test's cached result (or poison a later one).
    domain = "probe-count-test-1.example"
    with patch.object(subdomain_client, "_crt_sh_subdomains", return_value=[]), \
         patch.object(subdomain_client, "_resolve",
                       side_effect=lambda sub, d: {"hostname": f"{sub}.{d}", "ip": "1.2.3.4"}
                       if sub == "www" else None), \
         patch.object(subdomain_client, "_probe_http",
                       return_value={"scheme": "https", "status_code": 200, "final_url": f"https://www.{domain}",
                                     "server": "nginx", "title": "Example"}), \
         patch.object(subdomain_client, "_get_dns_info", return_value={}):
        result = subdomain_client.scan_domain(domain)

    assert result["http_probed_count"] == 1
    assert len(result["subdomains"]) == 1
    assert result["subdomains"][0]["http"]["status_code"] == 200


def test_scan_domain_no_resolved_hosts_skips_probing_without_crash():
    domain = "probe-count-test-2.example"
    with patch.object(subdomain_client, "_crt_sh_subdomains", return_value=[]), \
         patch.object(subdomain_client, "_resolve", return_value=None), \
         patch.object(subdomain_client, "_get_dns_info", return_value={}):
        result = subdomain_client.scan_domain(domain)

    assert result["subdomains_found"] == 0
    assert result["http_probed_count"] == 0
    assert result["subdomains"] == []


def test_scan_domain_probe_failure_leaves_http_none():
    domain = "probe-count-test-3.example"
    with patch.object(subdomain_client, "_crt_sh_subdomains", return_value=[]), \
         patch.object(subdomain_client, "_resolve",
                       side_effect=lambda sub, d: {"hostname": f"{sub}.{d}", "ip": "1.2.3.4"}
                       if sub == "www" else None), \
         patch.object(subdomain_client, "_probe_http", return_value=None), \
         patch.object(subdomain_client, "_get_dns_info", return_value={}):
        result = subdomain_client.scan_domain(domain)

    assert result["http_probed_count"] == 0
    assert result["subdomains"][0]["http"] is None


# ── Phase 2: subdomain takeover detection ────────────────────────────────

def test_check_takeover_high_confidence_on_cname_and_status_match():
    result = subdomain_client._check_takeover(
        "old.example.com", "old-example.github.io", {"status_code": 404}
    )
    assert result is not None
    assert result["service"] == "GitHub Pages"
    assert result["confidence"] == "HIGH"
    assert result["hostname"] == "old.example.com"
    assert result["cname"] == "old-example.github.io"


def test_check_takeover_medium_confidence_on_cname_only():
    result = subdomain_client._check_takeover(
        "old.example.com", "old-example.github.io", {"status_code": 200}
    )
    assert result is not None
    assert result["confidence"] == "MEDIUM"


def test_check_takeover_medium_confidence_when_no_http_data():
    result = subdomain_client._check_takeover(
        "old.example.com", "bucket.s3.amazonaws.com", None
    )
    assert result is not None
    assert result["service"] == "AWS S3"
    assert result["confidence"] == "MEDIUM"


def test_check_takeover_no_match_returns_none():
    assert subdomain_client._check_takeover(
        "www.example.com", "www.example.com.cdn.other.net", {"status_code": 200}
    ) is None


def test_check_takeover_none_cname_returns_none():
    assert subdomain_client._check_takeover("www.example.com", None, {"status_code": 404}) is None


def test_get_cname_returns_none_on_exception(monkeypatch):
    def fake_resolve(*args, **kwargs):
        raise Exception("NXDOMAIN")

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)
    assert subdomain_client._get_cname("nonexistent.example.com") is None


def test_get_cname_returns_target(monkeypatch):
    class _FakeAnswer:
        target = "some-target.github.io."

    def fake_resolve(hostname, rtype, lifetime=5):
        assert rtype == "CNAME"
        return [_FakeAnswer()]

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)
    assert subdomain_client._get_cname("old.example.com") == "some-target.github.io"


def test_scan_domain_detects_takeover_end_to_end(monkeypatch):
    domain = "takeover-test-1.example"

    def fake_resolve(hostname, rtype, lifetime=5):
        class _FakeAnswer:
            target = "dangling.github.io."
        if rtype == "CNAME":
            return [_FakeAnswer()]
        raise Exception("no record")

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)

    with patch.object(subdomain_client, "_crt_sh_subdomains", return_value=[]), \
         patch.object(subdomain_client, "_resolve",
                       side_effect=lambda sub, d: {"hostname": f"{sub}.{d}", "ip": "1.2.3.4"}
                       if sub == "www" else None), \
         patch.object(subdomain_client, "_probe_http",
                       return_value={"scheme": "https", "status_code": 404, "final_url": "x",
                                     "server": "", "title": None}), \
         patch.object(subdomain_client, "_get_dns_info", return_value={}):
        result = subdomain_client.scan_domain(domain)

    assert result["takeover_count"] == 1
    assert result["takeovers"][0]["service"] == "GitHub Pages"
    assert result["takeovers"][0]["confidence"] == "HIGH"
    assert result["subdomains"][0]["cname"] == "dangling.github.io"
    assert result["subdomains"][0]["takeover"]["service"] == "GitHub Pages"


def test_scan_domain_no_takeover_when_cname_absent(monkeypatch):
    domain = "takeover-test-2.example"

    def fake_resolve(hostname, rtype, lifetime=5):
        raise Exception("no record")

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)

    with patch.object(subdomain_client, "_crt_sh_subdomains", return_value=[]), \
         patch.object(subdomain_client, "_resolve",
                       side_effect=lambda sub, d: {"hostname": f"{sub}.{d}", "ip": "1.2.3.4"}
                       if sub == "www" else None), \
         patch.object(subdomain_client, "_probe_http", return_value=None), \
         patch.object(subdomain_client, "_get_dns_info", return_value={}):
        result = subdomain_client.scan_domain(domain)

    assert result["takeover_count"] == 0
    assert result["takeovers"] == []
    assert result["subdomains"][0]["cname"] is None
    assert result["subdomains"][0]["takeover"] is None
