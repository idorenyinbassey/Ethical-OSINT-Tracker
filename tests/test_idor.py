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


def test_other_user_cannot_access_async_export_job(app, client, user_a, user_b, case_of_a):
    # Owner starts an async export job and captures the job_id.
    login(client, user_a.username)
    resp = client.post(f"/cases/{case_of_a.id}/export/start", data={"fmt": "csv"})
    assert resp.status_code == 200
    job_id = resp.get_json()["job_id"]
    client.get("/logout")

    # A different user must not read the job status or download it.
    login(client, user_b.username)
    status = client.get(f"/cases/export/status/{job_id}")
    assert status.status_code == 403
    assert status.get_json()["status"] == "forbidden"

    download = client.get(f"/cases/export/download/{job_id}", follow_redirects=False)
    assert download.status_code == 403


def test_other_user_cannot_start_async_export(client, user_a, user_b, case_of_a):
    login(client, user_b.username)
    resp = client.post(f"/cases/{case_of_a.id}/export/start", data={"fmt": "csv"})
    assert resp.status_code == 403
