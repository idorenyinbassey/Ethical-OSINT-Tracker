"""Outbound alert delivery — webhook notifications for watchlist changes.

Configured like any other external service via Settings (service_name
"Notifications"): base_url holds the webhook URL (ntfy.sh, Discord,
Slack, or any endpoint that accepts a JSON POST), is_enabled gates
whether anything is sent at all. There is a single, instance-wide
configuration — like every other entry in Settings — not a per-user one.
"""
import logging
import httpx
from app.repositories.api_config_repository import get_by_service

logger = logging.getLogger(__name__)


def send_webhook(url: str, payload: dict) -> bool:
    """POST a JSON payload to a webhook URL.

    Never raises — logs and swallows every failure, since callers
    (notably the background scheduler) must never crash because a
    notification couldn't be delivered.
    """
    if not url:
        return False
    try:
        with httpx.Client(timeout=10) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            return True
    except httpx.TimeoutException:
        logger.error("Webhook notification timed out: %s", url)
        return False
    except httpx.HTTPStatusError as e:
        logger.error("Webhook notification HTTP %s: %s", e.response.status_code, url)
        return False
    except Exception:
        logger.exception("Webhook notification failed: %s", url)
        return False


def notify(subject: str, body: str, payload: dict | None = None) -> bool:
    """Send a notification via the configured webhook, if enabled.

    Returns True only if a webhook is configured, enabled, and the send
    succeeded — callers that care about delivery can check this, but
    should never treat a False return as fatal.
    """
    cfg = get_by_service("Notifications")
    if not cfg or not cfg.is_enabled or not cfg.base_url:
        return False
    full_payload = {"subject": subject, "body": body}
    if payload:
        full_payload.update(payload)
    return send_webhook(cfg.base_url, full_payload)
