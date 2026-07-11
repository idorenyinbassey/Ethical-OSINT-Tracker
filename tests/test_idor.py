"""IDOR / ownership enforcement tests (Issue #7)."""
from tests.conftest import login


def test_owner_can_view_own_case(client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.get(f"/cases/{case_of_a.id}")
    assert resp.status_code == 200


def test_other_user_cannot_view_case(client, user_a, user_b, case_of_a):
    login(client, user_b.username)
    resp = client.get(f"/cases/{case_of_a.id}")
    assert resp.status_code == 403


def test_other_user_cannot_delete_case(client, user_a, user_b, case_of_a):
    login(client, user_b.username)
    resp = client.post(f"/cases/{case_of_a.id}/delete")
    assert resp.status_code == 403


def test_other_user_cannot_export_case(client, user_a, user_b, case_of_a):
    login(client, user_b.username)
    resp = client.get(f"/cases/{case_of_a.id}/export/csv")
    assert resp.status_code == 403


def test_anonymous_redirected_to_login(client, case_of_a):
    resp = client.get(f"/cases/{case_of_a.id}", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("Location", "")
