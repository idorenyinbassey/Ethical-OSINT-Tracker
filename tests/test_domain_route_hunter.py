"""Integration: /investigate/domain route's Hunter.io Domain Search bonus
enrichment (merged into the persisted WHOIS result, mirroring how
Shodan/VirusTotal are bolted onto IP Lookup) and the separate, non-persisted
Email Finder action."""
from unittest.mock import patch
from tests.conftest import login
from app.repositories.investigation_repository import count_all


def test_domain_lookup_merges_hunter_domain_search_into_result(app, client, user_a, case_of_a):
    login(client, user_a.username)

    fake_whois = {"registrar": "Example Registrar", "status": "active", "domain": "example.com"}
    fake_hunter = {"organization": "Example Inc", "pattern": "{first}.{last}@example.com",
                   "total_emails": 1, "emails": [{"email": "jane.doe@example.com", "first_name": "Jane",
                                                    "last_name": "Doe", "position": "Engineer", "confidence": 90}]}

    with patch("app.routes.investigation.rdap_client.fetch_domain", return_value=fake_whois), \
         patch("app.routes.investigation.hunter_client.domain_search", return_value=fake_hunter):
        resp = client.post(
            "/investigate/domain",
            data={"query": "example.com", "case_id": case_of_a.id, "action": "whois"},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"jane.doe@example.com" in resp.data
    assert b"Example Inc" in resp.data


def test_domain_lookup_handles_hunter_not_configured(app, client, user_a, case_of_a):
    login(client, user_a.username)

    fake_whois = {"registrar": "Example Registrar", "status": "active", "domain": "example2.com"}

    with patch("app.routes.investigation.rdap_client.fetch_domain", return_value=fake_whois), \
         patch("app.routes.investigation.hunter_client.domain_search", return_value=None):
        resp = client.post(
            "/investigate/domain",
            data={"query": "example2.com", "case_id": case_of_a.id, "action": "whois"},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"Example Registrar" in resp.data


def test_find_email_action_returns_result_without_persisting_investigation(app, client, user_a, case_of_a):
    login(client, user_a.username)

    with app.app_context():
        before = count_all(user_id=user_a.id)

    fake_finder = {"found": True, "email": "jane.doe@example3.com", "score": 88, "position": "Manager"}
    with patch("app.routes.investigation.hunter_client.find_email", return_value=fake_finder) as mock_find:
        resp = client.post(
            "/investigate/domain",
            data={"query": "example3.com", "case_id": case_of_a.id, "action": "find_email",
                  "first_name": "Jane", "last_name": "Doe"},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"jane.doe@example3.com" in resp.data
    mock_find.assert_called_once_with("example3.com", "Jane", "Doe")

    with app.app_context():
        after = count_all(user_id=user_a.id)
    assert after == before


def test_find_email_action_requires_first_and_last_name(app, client, user_a, case_of_a):
    login(client, user_a.username)

    resp = client.post(
        "/investigate/domain",
        data={"query": "example4.com", "case_id": case_of_a.id, "action": "find_email",
              "first_name": "", "last_name": ""},
        follow_redirects=True,
    )

    assert resp.status_code == 200
    assert b"First and last name are required" in resp.data


def test_find_email_action_handles_not_configured(app, client, user_a, case_of_a):
    login(client, user_a.username)

    with patch("app.routes.investigation.hunter_client.find_email", return_value=None):
        resp = client.post(
            "/investigate/domain",
            data={"query": "example5.com", "case_id": case_of_a.id, "action": "find_email",
                  "first_name": "Jane", "last_name": "Doe"},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"Hunter.io is not configured" in resp.data
