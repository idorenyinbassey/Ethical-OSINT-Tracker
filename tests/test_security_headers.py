"""HTTP security headers (Issue #17)."""


def test_security_headers_present(client):
    resp = client.get("/login")
    headers = resp.headers
    assert "Content-Security-Policy" in headers
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in headers


def test_csp_restricts_default_src(client):
    resp = client.get("/login")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
