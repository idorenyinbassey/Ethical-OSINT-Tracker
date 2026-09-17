"""Integration: manual rescan route surfaces + dismisses the alert banner,
and shares alerting behavior with the scheduler via watchlist_scan_service."""
from unittest.mock import patch
from tests.conftest import login
from app.repositories.watchlist_repository import add_target, get_target


def _rescan(client, target_id, geo):
    with patch("app.services.ip_client.fetch_ip", return_value=geo), \
         patch("app.services.virustotal_client.fetch_virustotal", return_value=None), \
         patch("app.services.shodan_client.fetch_shodan", return_value=None), \
         patch("app.services.notification_service.notify"):
        return client.post(f"/investigate/watchlist/{target_id}/rescan", follow_redirects=True)


def test_first_rescan_does_not_flash_changed(app, client, user_a):
    login(client, user_a.username)
    with app.app_context():
        target = add_target(query="9.9.9.9", kind="ip", user_id=user_a.id)

    resp = _rescan(client, target.id, {"ip": "9.9.9.9", "city": "A"})
    assert resp.status_code == 200
    assert b"no changes detected" in resp.data.lower() or b"rescan complete" in resp.data.lower()
    with app.app_context():
        assert get_target(target.id).has_alert is False


def test_second_rescan_with_different_data_shows_alert_banner(app, client, user_a):
    login(client, user_a.username)
    with app.app_context():
        target = add_target(query="9.9.9.8", kind="ip", user_id=user_a.id)

    _rescan(client, target.id, {"ip": "9.9.9.8", "city": "A"})
    resp = _rescan(client, target.id, {"ip": "9.9.9.8", "city": "B — different"})
    assert resp.status_code == 200
    assert b"data changed" in resp.data.lower()

    # The watchlist page itself should render the dismissible alert banner.
    page = client.get("/investigate/watchlist")
    assert b"Dismiss" in page.data
    with app.app_context():
        assert get_target(target.id).has_alert is True


def test_dismiss_alert_clears_banner(app, client, user_a):
    login(client, user_a.username)
    with app.app_context():
        target = add_target(query="9.9.9.7", kind="ip", user_id=user_a.id)

    _rescan(client, target.id, {"ip": "9.9.9.7", "city": "A"})
    _rescan(client, target.id, {"ip": "9.9.9.7", "city": "B — different"})
    with app.app_context():
        assert get_target(target.id).has_alert is True

    resp = client.post(f"/investigate/watchlist/{target.id}/dismiss-alert", follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        cleared = get_target(target.id)
        assert cleared.has_alert is False
        assert cleared.alert_message == ""


def test_dismiss_alert_requires_ownership(app, client, user_a, user_b):
    with app.app_context():
        target = add_target(query="9.9.9.6", kind="ip", user_id=user_a.id)

    login(client, user_b.username)
    resp = client.post(f"/investigate/watchlist/{target.id}/dismiss-alert", follow_redirects=True)
    assert resp.status_code == 200
    assert b"not found" in resp.data.lower()
