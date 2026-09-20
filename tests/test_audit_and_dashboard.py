"""Part B: /audit is admin-only (viewing, export, and clear), the
Dashboard explains why "Total Investigations" can outlive every case
being deleted, and adding a watchlist target with no case flags that
its rescans will show up unlinked."""
import json

from tests.conftest import login


def test_audit_index_is_admin_only(client, user_a):
    login(client, user_a.username)
    resp = client.get("/audit")
    assert resp.status_code == 403


def test_audit_export_is_admin_only(client, user_a):
    login(client, user_a.username)
    resp = client.get("/audit/export")
    assert resp.status_code == 403


def test_audit_clear_is_admin_only(client, user_a):
    login(client, user_a.username)
    resp = client.post("/audit/clear", data={"password": "irrelevant"})
    assert resp.status_code == 403


def test_admin_can_view_audit_log(client, admin_user):
    login(client, admin_user.username)
    resp = client.get("/audit")
    assert resp.status_code == 200


def test_admin_can_export_audit_log_as_csv(app, client, admin_user):
    from app.utils.audit import log as audit_log

    with app.app_context():
        audit_log("login", user_id=admin_user.id, username=admin_user.username)
    login(client, admin_user.username)

    resp = client.get("/audit/export")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    body = resp.data.decode()
    assert "login" in body


def test_admin_clear_with_wrong_password_leaves_log_intact(app, client, admin_user):
    from tests.conftest import PASSWORD
    from app.utils.audit import log as audit_log
    from app.repositories.audit_log_repository import list_logs

    with app.app_context():
        audit_log("login", user_id=admin_user.id, username=admin_user.username)
    login(client, admin_user.username)

    resp = client.post("/audit/clear", data={"password": "definitely-wrong"})
    assert resp.status_code == 302
    with app.app_context():
        assert len(list_logs()) >= 1


def test_admin_clear_with_correct_password_deletes_all_logs(app, client, admin_user):
    from tests.conftest import PASSWORD
    from app.utils.audit import log as audit_log
    from app.repositories.audit_log_repository import list_logs

    with app.app_context():
        audit_log("login", user_id=admin_user.id, username=admin_user.username)
    login(client, admin_user.username)

    resp = client.post("/audit/clear", data={"password": PASSWORD})
    assert resp.status_code == 302
    with app.app_context():
        # The clear itself is audit-logged, so exactly one row (the
        # "audit.clear" entry) should remain — not zero, not the old ones.
        remaining = list_logs()
        assert len(remaining) == 1
        assert remaining[0].action == "audit.clear"


# ── Dashboard ad-hoc investigation count ─────────────────────────────────────

def test_dashboard_shows_ad_hoc_investigation_note(app, client, user_a):
    from app.repositories.investigation_repository import create_investigation

    with app.app_context():
        create_investigation(kind="ip", query="8.8.8.8", result_json=json.dumps({"v": 1}),
                             user_id=user_a.id, case_id=None)
    login(client, user_a.username)

    resp = client.get("/")
    body = resp.data.decode()
    assert "not linked to any case" in body


def test_dashboard_omits_ad_hoc_note_when_none_exist(app, client, user_a, case_of_a):
    from app.repositories.investigation_repository import create_investigation

    with app.app_context():
        create_investigation(kind="ip", query="8.8.8.8", result_json=json.dumps({"v": 1}),
                             user_id=user_a.id, case_id=case_of_a.id)
    login(client, user_a.username)

    resp = client.get("/")
    assert "not linked to any case" not in resp.data.decode()


# ── watchlist_add() no-case notice ───────────────────────────────────────────

def test_watchlist_add_without_case_flashes_explanatory_note(client, user_a):
    login(client, user_a.username)
    resp = client.post("/investigate/watchlist/add", data={
        "query": "8.8.8.8", "kind": "ip",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"its future rescans will show up as investigations not linked to any case" in resp.data


def test_watchlist_add_with_case_does_not_flash_note(client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.post("/investigate/watchlist/add", data={
        "query": "8.8.8.8", "kind": "ip", "case_id": str(case_of_a.id),
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"its future rescans will show up as investigations not linked to any case" not in resp.data
