"""Integration: /investigate/subdomain route renders the HTTP-probe data
(status badge, server/title) that app.services.subdomain_client now returns."""
from unittest.mock import patch
from tests.conftest import login


def test_subdomain_scan_renders_http_probe_data(app, client, user_a, case_of_a):
    login(client, user_a.username)

    fake_result = {
        "domain": "example.com",
        "subdomains_found": 1,
        "ct_subdomains": 0,
        "http_probed_count": 1,
        "dns": {},
        "subdomains": [
            {
                "hostname": "www.example.com",
                "ip": "1.2.3.4",
                "http": {
                    "scheme": "https",
                    "status_code": 200,
                    "final_url": "https://www.example.com/",
                    "server": "nginx",
                    "title": "Example Domain",
                },
            }
        ],
    }

    with patch("app.services.subdomain_client.scan_domain", return_value=fake_result):
        resp = client.post(
            "/investigate/subdomain",
            data={"query": "example.com", "case_id": case_of_a.id},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"www.example.com" in resp.data
    assert b"200" in resp.data
    assert b"nginx" in resp.data
    assert b"Example Domain" in resp.data


def test_subdomain_scan_handles_missing_http_probe_gracefully(app, client, user_a, case_of_a):
    """A host that resolved but couldn't be probed (http: None) must not
    break the template."""
    login(client, user_a.username)

    fake_result = {
        "domain": "example.com",
        "subdomains_found": 1,
        "ct_subdomains": 0,
        "http_probed_count": 0,
        "dns": {},
        "subdomains": [{"hostname": "mail.example.com", "ip": "5.6.7.8", "http": None}],
    }

    with patch("app.services.subdomain_client.scan_domain", return_value=fake_result):
        resp = client.post(
            "/investigate/subdomain",
            data={"query": "example.com", "case_id": case_of_a.id},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"mail.example.com" in resp.data


def test_subdomain_scan_renders_takeover_candidates(app, client, user_a, case_of_a):
    login(client, user_a.username)

    fake_result = {
        "domain": "example.com",
        "subdomains_found": 1,
        "ct_subdomains": 0,
        "http_probed_count": 1,
        "takeover_count": 1,
        "takeovers": [
            {"hostname": "old.example.com", "cname": "old.github.io", "service": "GitHub Pages", "confidence": "HIGH"}
        ],
        "dns": {},
        "subdomains": [
            {
                "hostname": "old.example.com",
                "ip": "1.2.3.4",
                "cname": "old.github.io",
                "takeover": {"hostname": "old.example.com", "cname": "old.github.io",
                             "service": "GitHub Pages", "confidence": "HIGH"},
                "http": {"scheme": "https", "status_code": 404, "final_url": "https://old.example.com/",
                         "server": "", "title": None},
            }
        ],
    }

    with patch("app.services.subdomain_client.scan_domain", return_value=fake_result):
        resp = client.post(
            "/investigate/subdomain",
            data={"query": "example.com", "case_id": case_of_a.id},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"Possible Takeovers" in resp.data
    assert b"GitHub Pages" in resp.data
    assert b"possible takeover" in resp.data.lower()
