"""app.routes.cases.view_investigation() — lets an investigator open a past
scan (while its case still exists) and read its stored fields, so values
found in one tool's result (an email, a domain, a linked profile) can be
copied into a follow-up scan with another tool."""
import json

from tests.conftest import login


def _seed_investigation(app, user_id, case_id, result):
    from app.repositories.investigation_repository import create_investigation
    with app.app_context():
        return create_investigation(
            kind="social", query="johndoe", result_json=json.dumps(result),
            user_id=user_id, case_id=case_id, confidence="CONFIRMED",
        )


def test_view_investigation_shows_nested_fields(app, client, user_a, case_of_a):
    login(client, user_a.username)
    result = {
        "username": "johndoe",
        "results": [
            {"site": "GitHub", "found": True, "email": "johndoe@example.com"},
        ],
    }
    inv = _seed_investigation(app, user_a.id, case_of_a.id, result)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "johndoe@example.com" in body
    assert "GitHub" in body


def test_view_investigation_denies_user_without_case_access(app, client, user_a, user_b, case_of_a):
    inv = _seed_investigation(app, user_a.id, case_of_a.id, {"v": 1})
    login(client, user_b.username)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    assert resp.status_code == 403


def test_view_investigation_rejects_mismatched_case_id(app, client, user_a, case_of_a):
    """An investigation belonging to a DIFFERENT case must 404 even when
    the requester has read access to the case_id in the URL — otherwise a
    user could view any investigation on the site just by guessing its id
    while supplying one of their own case ids."""
    from app.repositories.case_repository import create_case

    with app.app_context():
        other_case = create_case("Other Case", "", owner_user_id=user_a.id)
    inv = _seed_investigation(app, user_a.id, other_case.id, {"v": 1})

    login(client, user_a.username)
    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    assert resp.status_code == 404


def test_view_investigation_handles_malformed_result_json(app, client, user_a, case_of_a):
    from app.repositories.investigation_repository import create_investigation

    login(client, user_a.username)
    with app.app_context():
        inv = create_investigation(
            kind="ip", query="8.8.8.8", result_json="{not valid json",
            user_id=user_a.id, case_id=case_of_a.id,
        )

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    assert resp.status_code == 200
    assert b"Could not read" in resp.data


def test_view_investigation_handles_empty_result(app, client, user_a, case_of_a):
    from app.repositories.investigation_repository import create_investigation

    login(client, user_a.username)
    with app.app_context():
        inv = create_investigation(
            kind="ip", query="8.8.8.8", result_json="",
            user_id=user_a.id, case_id=case_of_a.id,
        )

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    assert resp.status_code == 200
    assert b"no stored result" in resp.data


def test_view_investigation_nonexistent_returns_404(app, client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.get(f"/cases/{case_of_a.id}/investigations/999999")
    assert resp.status_code == 404
