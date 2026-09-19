"""Social Search's "Profiles Found" cards must show emails/linked domains
(already extracted server-side by social_client._extract_contact_info(),
and already wired into the entity graph) right alongside the profile
picture — not just in the raw per-tool history dump or the graph, which is
where they only appeared before this."""
import json
from unittest.mock import patch

from tests.conftest import login


def test_found_profile_card_shows_picture_email_and_linked_domain(app, client, user_a, case_of_a):
    fake_result = {
        "username": "alice_j",
        "found_count": 1,
        "confirmed_count": 1,
        "total_checked": 1,
        "results": [
            {
                "site": "GitHub",
                "found": True,
                "confidence": "high",
                "status_code": 200,
                "url": "https://github.com/alice_j",
                "profile_image": "https://avatars.githubusercontent.com/u/2?v=4",
                "display_name": "Alice J",
                "bio": "Engineer.",
                "emails": ["alice.j@example.com"],
                "linked_domains": ["alice-j.dev"],
            },
        ],
    }
    login(client, user_a.username)

    with patch("app.routes.investigation.social_client.search_username", return_value=fake_result):
        resp = client.post(
            "/investigate/social",
            data={"query": "alice_j", "case_id": str(case_of_a.id)},
        )

    assert resp.status_code == 200
    body = resp.data.decode()
    assert "https://avatars.githubusercontent.com/u/2?v=4" in body
    assert "alice.j@example.com" in body
    assert "alice-j.dev" in body


def test_found_profile_card_omits_contact_block_when_none_extracted(app, client, user_a, case_of_a):
    """A found profile with no mailto:/rel="me" signals on the page must not
    render an empty contact-info block."""
    fake_result = {
        "username": "bob_k",
        "found_count": 1,
        "confirmed_count": 1,
        "total_checked": 1,
        "results": [
            {
                "site": "GitHub",
                "found": True,
                "confidence": "high",
                "status_code": 200,
                "url": "https://github.com/bob_k",
            },
        ],
    }
    login(client, user_a.username)

    with patch("app.routes.investigation.social_client.search_username", return_value=fake_result):
        resp = client.post(
            "/investigate/social",
            data={"query": "bob_k", "case_id": str(case_of_a.id)},
        )

    assert resp.status_code == 200
    assert "mailto:" not in resp.data.decode()
