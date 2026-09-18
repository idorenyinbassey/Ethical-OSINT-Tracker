"""app.services.notification_service — webhook delivery for watchlist alerts."""
from unittest.mock import patch, MagicMock
from app.services.notification_service import notify, send_webhook
from app.repositories.api_config_repository import create_or_update_config, delete_config


def test_notify_noop_when_not_configured(app):
    with app.app_context():
        delete_config("Notifications")
        assert notify("subject", "body") is False


def test_notify_noop_when_disabled(app):
    with app.app_context():
        try:
            create_or_update_config(
                service_name="Notifications", api_key="", base_url="https://example.com/hook",
                is_enabled=False,
            )
            with patch("app.services.notification_service.httpx.Client") as mock_client:
                assert notify("subject", "body") is False
                mock_client.assert_not_called()
        finally:
            delete_config("Notifications")


def test_notify_sends_webhook_when_enabled(app):
    with app.app_context():
        try:
            create_or_update_config(
                service_name="Notifications", api_key="", base_url="https://example.com/hook",
                is_enabled=True,
            )
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            with patch("app.services.notification_service.httpx.Client") as mock_client_cls:
                mock_client = mock_client_cls.return_value.__enter__.return_value
                mock_client.post.return_value = mock_response

                result = notify("Watchlist alert", "1.2.3.4 changed", payload={"target_id": 1})

            assert result is True
            mock_client.post.assert_called_once()
            args, kwargs = mock_client.post.call_args
            assert args[0] == "https://example.com/hook"
            assert kwargs["json"]["subject"] == "Watchlist alert"
            assert kwargs["json"]["target_id"] == 1
        finally:
            delete_config("Notifications")


def test_send_webhook_swallows_timeout():
    import httpx
    with patch("app.services.notification_service.httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.post.side_effect = httpx.TimeoutException("timed out")
        assert send_webhook("https://example.com/hook", {"a": 1}) is False


def test_send_webhook_swallows_http_error():
    import httpx
    with patch("app.services.notification_service.httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.post.return_value = mock_response
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response,
        )
        assert send_webhook("https://example.com/hook", {"a": 1}) is False


def test_send_webhook_empty_url_is_noop():
    assert send_webhook("", {"a": 1}) is False
