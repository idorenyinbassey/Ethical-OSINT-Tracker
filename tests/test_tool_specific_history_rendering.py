"""Social Search and Breach Check history entries — both on the tool's own
"previous results in this case" section and on the case-detail scan
viewer (cases/investigation_view.html) — render using each tool's own
live-page styling (investigation/_tool_result_macros.html: profile cards
with a favicon/avatar, Found/Possible badge, and breach cards with a
data_classes chip) instead of the generic recursive key/value dump every
other kind still uses (investigation/_result_macros.html)."""
import json

from tests.conftest import login


def _seed(app, user_id, case_id, kind, query, result):
    from app.repositories.investigation_repository import create_investigation
    with app.app_context():
        return create_investigation(
            kind=kind, query=query, result_json=json.dumps(result),
            user_id=user_id, case_id=case_id, confidence="CONFIRMED",
        )


SOCIAL_RESULT = {
    "username": "alice_j",
    "found_count": 1,
    "confirmed_count": 1,
    "total_checked": 3,
    "results": [
        {
            "site": "GitHub",
            "found": True,
            "confidence": "high",
            "status_code": 200,
            "url": "https://github.com/alice_j",
        },
    ],
}

BREACH_RESULT = {
    "breaches": [
        {"name": "ExampleCorp", "date": "2020-01-01", "data_classes": ["Emails", "Passwords"]},
    ],
}


# ── Tool's own "previous results in this case" section ──────────────────────

def test_social_history_renders_profile_card_not_generic_dump(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "social", "alice_j", SOCIAL_RESULT)
    login(client, user_a.username)

    resp = client.get(f"/investigate/social?case_id={case_of_a.id}")
    body = resp.data.decode()
    assert resp.status_code == 200
    assert "Found</span>" in body
    assert 'href="https://github.com/alice_j"' in body
    # The generic renderer would show raw field labels like this; the
    # specialized card renderer never does.
    assert "<dt " not in body


def test_breach_history_renders_breach_card_not_generic_dump(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "breach", "user@example.com", BREACH_RESULT)
    login(client, user_a.username)

    resp = client.get(f"/investigate/breach?case_id={case_of_a.id}")
    body = resp.data.decode()
    assert resp.status_code == 200
    assert "ExampleCorp" in body
    assert "Emails" in body and "Passwords" in body
    assert "<dt " not in body


def test_breach_history_handles_null_breaches_gracefully(app, client, user_a, case_of_a):
    """A past breach check that failed/was disabled stores {"breaches": null}
    — history must show a short note, not crash on `breaches|length`."""
    _seed(app, user_a.id, case_of_a.id, "breach", "user@example.com", {"breaches": None})
    login(client, user_a.username)

    resp = client.get(f"/investigate/breach?case_id={case_of_a.id}")
    assert resp.status_code == 200
    assert b"Breach data unavailable for this entry." in resp.data


# ── Case-detail scan viewer ──────────────────────────────────────────────────

def test_case_scan_viewer_renders_social_profile_card(app, client, user_a, case_of_a):
    inv = _seed(app, user_a.id, case_of_a.id, "social", "alice_j", SOCIAL_RESULT)
    login(client, user_a.username)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    body = resp.data.decode()
    assert resp.status_code == 200
    assert "Found</span>" in body
    assert 'href="https://github.com/alice_j"' in body
    assert "<dt " not in body


def test_case_scan_viewer_renders_breach_card(app, client, user_a, case_of_a):
    inv = _seed(app, user_a.id, case_of_a.id, "breach", "user@example.com", BREACH_RESULT)
    login(client, user_a.username)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    body = resp.data.decode()
    assert resp.status_code == 200
    assert "ExampleCorp" in body
    assert "Emails" in body and "Passwords" in body


# ── Out-of-scope kinds keep the generic renderer ────────────────────────────

def test_ip_history_still_uses_generic_renderer(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "ip", "8.8.8.8", {"geo": {"city": "Mountain View"}})
    login(client, user_a.username)

    resp = client.get(f"/investigate/ip?case_id={case_of_a.id}")
    body = resp.data.decode()
    assert resp.status_code == 200
    assert "<dt " in body
