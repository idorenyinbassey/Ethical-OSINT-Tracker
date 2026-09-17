"""app.services.watchlist_scan_service — shared hash-diff/alert logic used
by both the scheduler's automatic rescan and the manual "Rescan" route."""
from unittest.mock import patch
from app.services.watchlist_scan_service import finalize_scan
from app.repositories.watchlist_repository import add_target, get_target


def test_first_scan_never_counts_as_changed(app, user_a):
    """A target's very first check has nothing to diff against — must not
    alert (this was the manual route's bug: it compared against an empty
    last_result_hash and always reported 'changed' on the first rescan)."""
    with app.app_context():
        target = add_target(query="1.2.3.4", kind="ip", user_id=user_a.id)
        with patch("app.services.watchlist_scan_service.notify") as mock_notify:
            changed = finalize_scan(target, {"data": "first result"})
        assert changed is False
        mock_notify.assert_not_called()
        refreshed = get_target(target.id)
        assert refreshed.has_alert is False


def test_scan_sets_alert_and_notifies_on_change(app, user_a):
    with app.app_context():
        target = add_target(query="1.2.3.5", kind="ip", user_id=user_a.id)
        with patch("app.services.watchlist_scan_service.notify") as mock_notify:
            finalize_scan(target, {"data": "result A"})
            refreshed = get_target(target.id)
            changed = finalize_scan(refreshed, {"data": "result B — different"})

        assert changed is True
        mock_notify.assert_called_once()
        refreshed = get_target(target.id)
        assert refreshed.has_alert is True
        assert "changed" in refreshed.alert_message.lower()


def test_scan_no_alert_when_result_unchanged(app, user_a):
    with app.app_context():
        target = add_target(query="1.2.3.6", kind="ip", user_id=user_a.id)
        with patch("app.services.watchlist_scan_service.notify") as mock_notify:
            finalize_scan(target, {"data": "same"})
            refreshed = get_target(target.id)
            changed = finalize_scan(refreshed, {"data": "same"})

        assert changed is False
        mock_notify.assert_not_called()
        refreshed = get_target(target.id)
        assert refreshed.has_alert is False


def test_clear_alert_resets_state(app, user_a):
    from app.repositories.watchlist_repository import clear_alert
    with app.app_context():
        target = add_target(query="1.2.3.7", kind="ip", user_id=user_a.id)
        with patch("app.services.watchlist_scan_service.notify"):
            finalize_scan(target, {"data": "v1"})
            refreshed = get_target(target.id)
            finalize_scan(refreshed, {"data": "v2"})

        assert get_target(target.id).has_alert is True
        clear_alert(target.id)
        cleared = get_target(target.id)
        assert cleared.has_alert is False
        assert cleared.alert_message == ""


def test_notification_failure_does_not_break_scan(app, user_a):
    """notify() raising must not prevent the scan from persisting state —
    finalize_scan wraps the notify() call in its own try/except."""
    with app.app_context():
        target = add_target(query="1.2.3.8", kind="ip", user_id=user_a.id)
        with patch("app.services.watchlist_scan_service.notify", side_effect=RuntimeError("boom")):
            finalize_scan(target, {"data": "v1"})
            refreshed = get_target(target.id)
            changed = finalize_scan(refreshed, {"data": "v2"})

        assert changed is True  # did not raise, and correctly reports the change
        assert get_target(target.id).has_alert is True
