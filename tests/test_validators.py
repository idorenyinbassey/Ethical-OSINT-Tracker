"""SSRF URL validation (Issue #8) and social username validation (Issue #12)."""
import pytest

from app.utils.validators import validate_base_url
from app.routes.investigation import USERNAME_PATTERN


@pytest.mark.parametrize("url", [
    "http://169.254.169.254",       # AWS metadata (link-local)
    "http://127.0.0.1",             # loopback
    "http://10.0.0.1",              # RFC1918
    "http://192.168.1.1",           # RFC1918
    "http://172.16.0.1",            # RFC1918
    "https://localhost",            # reserved hostname
    "https://metadata.google.internal",  # GCP metadata
    "ftp://example.com",            # wrong scheme
])
def test_ssrf_urls_rejected(url):
    ok, _ = validate_base_url(url)
    assert ok is False


@pytest.mark.parametrize("url", [
    "https://api.github.com",
    "https://api.shodan.io",
    "https://apilayer.net/api",
    "",  # empty means "use default"
])
def test_public_urls_accepted(url):
    ok, _ = validate_base_url(url)
    assert ok is True


@pytest.mark.parametrize("bad", ["{username.__class__}", "../admin", "a" * 51, "user name", ""])
def test_invalid_usernames_rejected(bad):
    assert not USERNAME_PATTERN.match(bad)


@pytest.mark.parametrize("good", ["valid_user123", "john.doe", "a-b_c", "X"])
def test_valid_usernames_accepted(good):
    assert USERNAME_PATTERN.match(good)


def test_social_route_rejects_bad_username(client, user_a, case_of_a):
    from tests.conftest import login
    login(client, user_a.username)
    # The investigation blueprint requires an owned case + selected case_id
    # before the tool runs; the username validation happens after that guard.
    resp = client.post(
        "/investigate/social",
        data={"query": "{username.__class__}", "case_id": str(case_of_a.id)},
    )
    assert resp.status_code == 400
