"""Integration: /investigate/paste-monitor route + watchlist dispatch for
the "paste_leak" kind."""
from unittest.mock import patch
from tests.conftest import login


def test_paste_monitor_disabled_shows_flash(app, client, user_a, case_of_a):
    login(client, user_a.username)
    with patch("app.services.paste_client.check_pastes", return_value=None):
        resp = client.post(
            "/investigate/paste-monitor",
            data={"query": "route-test-1@example.com", "case_id": case_of_a.id},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"disabled" in resp.data.lower()


def test_paste_monitor_zero_hits(app, client, user_a, case_of_a):
    login(client, user_a.username)
    with patch("app.services.paste_client.check_pastes", return_value=[]):
        resp = client.post(
            "/investigate/paste-monitor",
            data={"query": "route-test-2@example.com", "case_id": case_of_a.id},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"No leak hits found" in resp.data


def test_paste_monitor_renders_hits(app, client, user_a, case_of_a):
    login(client, user_a.username)
    fake_pastes = [{"id": "abc", "url": "https://pastebin.com/abc", "date": "2024-01-01", "snippet": "leaked data"}]
    with patch("app.services.paste_client.check_pastes", return_value=fake_pastes):
        resp = client.post(
            "/investigate/paste-monitor",
            data={"query": "route-test-3@example.com", "case_id": case_of_a.id},
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"pastebin.com/abc" in resp.data
    assert b"leaked data" in resp.data


def test_paste_monitor_requires_query(app, client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.post(
        "/investigate/paste-monitor",
        data={"query": "", "case_id": case_of_a.id},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"query is required" in resp.data.lower()


def test_watchlist_add_accepts_paste_leak_kind(app, client, user_a):
    login(client, user_a.username)
    resp = client.post(
        "/investigate/watchlist/add",
        data={"query": "route-test-4@example.com", "kind": "paste_leak"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"added to watchlist" in resp.data


def test_fetch_target_data_dispatches_to_paste_client(app, user_a):
    from app.repositories.watchlist_repository import add_target
    from app.services.watchlist_scan_service import fetch_target_data

    with app.app_context():
        target = add_target(query="route-test-5@example.com", kind="paste_leak", user_id=user_a.id)
        with patch("app.services.paste_client.check_pastes", return_value=[]) as mock_check:
            result = fetch_target_data(target)

    mock_check.assert_called_once_with("route-test-5@example.com")
    assert result == {"query": "route-test-5@example.com", "pastes": []}


def test_watchlist_rescan_dispatches_to_paste_client(app, client, user_a):
    from app.repositories.watchlist_repository import add_target

    login(client, user_a.username)
    with app.app_context():
        target = add_target(query="route-test-6@example.com", kind="paste_leak", user_id=user_a.id)
        target_id = target.id

    with patch("app.services.paste_client.check_pastes", return_value=[{"id": "x", "url": "u", "date": "d", "snippet": "s"}]):
        resp = client.post(f"/investigate/watchlist/{target_id}/rescan", follow_redirects=True)

    assert resp.status_code == 200
    assert b"Rescan complete" in resp.data
