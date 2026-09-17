"""Integration: /investigate/typosquat route + watchlist dispatch for the
"typosquat" kind."""
from unittest.mock import patch
from tests.conftest import login


def test_typosquat_scan_renders_registered_hits(app, client, user_a, case_of_a):
    login(client, user_a.username)

    fake_result = {
        "domain": "example.com",
        "permutations_generated": 10,
        "registered_count": 1,
        "unregistered_count": 9,
        "registered": [
            {"domain": "examp1e.com", "ip": "1.2.3.4", "registrar": "Evil Registrar", "created": "2024-01-01"}
        ],
    }

    with patch("app.services.typosquat_client.scan_typosquats", return_value=fake_result):
        resp = client.post(
            "/investigate/typosquat",
            data={"query": "example.com", "case_id": case_of_a.id},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"examp1e.com" in resp.data
    assert b"Evil Registrar" in resp.data


def test_typosquat_scan_no_hits_renders_empty_state(app, client, user_a, case_of_a):
    login(client, user_a.username)

    fake_result = {
        "domain": "example.com",
        "permutations_generated": 10,
        "registered_count": 0,
        "unregistered_count": 10,
        "registered": [],
    }

    with patch("app.services.typosquat_client.scan_typosquats", return_value=fake_result):
        resp = client.post(
            "/investigate/typosquat",
            data={"query": "example.com", "case_id": case_of_a.id},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"No registered lookalike domains found" in resp.data


def test_typosquat_requires_domain(app, client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.post(
        "/investigate/typosquat",
        data={"query": "", "case_id": case_of_a.id},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Domain is required" in resp.data


def test_watchlist_add_accepts_typosquat_kind(app, client, user_a):
    login(client, user_a.username)
    resp = client.post(
        "/investigate/watchlist/add",
        data={"query": "example.com", "kind": "typosquat"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"added to watchlist" in resp.data


def test_fetch_target_data_dispatches_to_typosquat_client(app, user_a):
    from app.repositories.watchlist_repository import add_target
    from app.services.watchlist_scan_service import fetch_target_data

    with app.app_context():
        target = add_target(query="example.com", kind="typosquat", user_id=user_a.id)
        with patch("app.services.typosquat_client.scan_typosquats",
                   return_value={"domain": "example.com", "registered_count": 0, "registered": []}) as mock_scan:
            result = fetch_target_data(target)

    mock_scan.assert_called_once_with("example.com")
    assert result["registered_count"] == 0
