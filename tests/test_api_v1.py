"""app.routes.api_v1 — the stateless, API-key-authenticated /api/v1 surface."""
from unittest.mock import patch
from app.repositories.api_key_repository import create_api_key
from app.repositories.watchlist_repository import add_target, get_target


def _key_for(app, user):
    with app.app_context():
        _, raw = create_api_key(user.id, label="test")
        return raw


def test_no_key_is_401(client):
    resp = client.get("/api/v1/cases")
    assert resp.status_code == 401
    assert resp.get_json()["error"]


def test_garbage_key_is_401(client):
    resp = client.get("/api/v1/cases", headers={"X-API-Key": "not-a-real-key"})
    assert resp.status_code == 401


def test_revoked_key_is_401(app, client, user_a):
    with app.app_context():
        from app.repositories.api_key_repository import create_api_key, revoke_key
        key, raw = create_api_key(user_a.id)
        revoke_key(key.id, user_id=user_a.id)
    resp = client.get("/api/v1/cases", headers={"X-API-Key": raw})
    assert resp.status_code == 401


def test_bearer_auth_style_works(app, client, user_a):
    raw = _key_for(app, user_a)
    resp = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {raw}"})
    assert resp.status_code == 200


def test_list_cases_scoped_to_key_owner(app, client, user_a, user_b, case_of_a):
    raw_a = _key_for(app, user_a)
    raw_b = _key_for(app, user_b)

    resp = client.get("/api/v1/cases", headers={"X-API-Key": raw_a})
    assert resp.status_code == 200
    ids = {c["id"] for c in resp.get_json()["cases"]}
    assert case_of_a.id in ids

    resp = client.get("/api/v1/cases", headers={"X-API-Key": raw_b})
    assert resp.status_code == 200
    ids = {c["id"] for c in resp.get_json()["cases"]}
    assert case_of_a.id not in ids


def test_get_case_forbidden_for_non_owner(app, client, user_a, user_b, case_of_a):
    raw_b = _key_for(app, user_b)
    resp = client.get(f"/api/v1/cases/{case_of_a.id}", headers={"X-API-Key": raw_b})
    assert resp.status_code == 403


def test_get_case_404_for_nonexistent(app, client, user_a):
    raw_a = _key_for(app, user_a)
    resp = client.get("/api/v1/cases/999999", headers={"X-API-Key": raw_a})
    assert resp.status_code == 404


def test_shared_case_visible_to_team_member_via_api(app, client, user_a, user_b, case_of_a, team_a):
    from app.repositories.team_repository import add_team_member
    from app.repositories.case_repository import update_case
    with app.app_context():
        add_team_member(team_a.id, user_b.id, role="analyst")
        update_case(case_of_a.id, team_id=team_a.id)

    raw_b = _key_for(app, user_b)
    resp = client.get(f"/api/v1/cases/{case_of_a.id}", headers={"X-API-Key": raw_b})
    assert resp.status_code == 200


def test_case_investigations_list(app, client, user_a, case_of_a):
    with app.app_context():
        from app.repositories.investigation_repository import create_investigation
        create_investigation(kind="ip", query="1.2.3.4", result_json="{}",
                              user_id=user_a.id, case_id=case_of_a.id)
    raw_a = _key_for(app, user_a)
    resp = client.get(f"/api/v1/cases/{case_of_a.id}/investigations", headers={"X-API-Key": raw_a})
    assert resp.status_code == 200
    kinds = {i["kind"] for i in resp.get_json()["investigations"]}
    assert "ip" in kinds


def test_get_investigation_standalone_scoped_to_owner(app, client, user_a, user_b):
    with app.app_context():
        from app.repositories.investigation_repository import create_investigation
        inv = create_investigation(kind="ip", query="5.5.5.5", result_json="{}", user_id=user_a.id)

    raw_a = _key_for(app, user_a)
    raw_b = _key_for(app, user_b)
    assert client.get(f"/api/v1/investigations/{inv.id}", headers={"X-API-Key": raw_a}).status_code == 200
    assert client.get(f"/api/v1/investigations/{inv.id}", headers={"X-API-Key": raw_b}).status_code == 403


def test_watchlist_list_scoped_to_key_owner(app, client, user_a, user_b):
    with app.app_context():
        add_target(query="9.9.9.9", kind="ip", user_id=user_a.id)
    raw_a = _key_for(app, user_a)
    raw_b = _key_for(app, user_b)

    resp = client.get("/api/v1/watchlist", headers={"X-API-Key": raw_a})
    assert resp.status_code == 200
    assert len(resp.get_json()["watchlist"]) >= 1

    resp = client.get("/api/v1/watchlist", headers={"X-API-Key": raw_b})
    assert resp.status_code == 200
    assert all(t["query"] != "9.9.9.9" for t in resp.get_json()["watchlist"])


def test_rescan_via_api_updates_target_and_shares_alert_logic(app, client, user_a):
    with app.app_context():
        target = add_target(query="1.1.1.1", kind="ip", user_id=user_a.id)
    raw_a = _key_for(app, user_a)

    with patch("app.services.ip_client.fetch_ip", return_value={"ip": "1.1.1.1", "city": "A"}), \
         patch("app.services.notification_service.notify"):
        r1 = client.post(f"/api/v1/watchlist/{target.id}/rescan", headers={"X-API-Key": raw_a})
        assert r1.status_code == 200
        assert r1.get_json()["changed"] is False  # first scan never counts as changed

        with patch("app.services.ip_client.fetch_ip", return_value={"ip": "1.1.1.1", "city": "B"}):
            r2 = client.post(f"/api/v1/watchlist/{target.id}/rescan", headers={"X-API-Key": raw_a})
        assert r2.status_code == 200
        assert r2.get_json()["changed"] is True

    with app.app_context():
        assert get_target(target.id).has_alert is True


def test_rescan_forbidden_for_other_users_target(app, client, user_a, user_b):
    with app.app_context():
        target = add_target(query="2.2.2.2", kind="ip", user_id=user_a.id)
    raw_b = _key_for(app, user_b)
    resp = client.post(f"/api/v1/watchlist/{target.id}/rescan", headers={"X-API-Key": raw_b})
    assert resp.status_code == 404


def test_rescan_rate_limited(app, client, user_a):
    with app.app_context():
        target = add_target(query="3.3.3.3", kind="ip", user_id=user_a.id)
    raw_a = _key_for(app, user_a)

    with patch("app.services.ip_client.fetch_ip", return_value={"ip": "3.3.3.3"}), \
         patch("app.services.notification_service.notify"):
        statuses = [
            client.post(f"/api/v1/watchlist/{target.id}/rescan", headers={"X-API-Key": raw_a}).status_code
            for _ in range(21)
        ]
    assert 429 in statuses
