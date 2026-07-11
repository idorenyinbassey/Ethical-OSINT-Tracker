"""Auth route tests: login, rate limiting, registration controls (Issue #6)."""
import pytest

from app.config import Config
from tests.conftest import login, PASSWORD


def test_valid_login_redirects(client, user_a):
    resp = login(client, user_a.username)
    assert resp.status_code == 302
    assert "/login" not in resp.headers.get("Location", "")


def test_invalid_password_stays_on_login(client, user_a):
    resp = login(client, user_a.username, password="wrong")
    assert resp.status_code == 200
    assert b"Invalid username or password" in resp.data


def test_login_rate_limited_after_10_attempts(client, user_a):
    # 10 attempts within the window are allowed (they render the login page).
    for _ in range(10):
        resp = login(client, user_a.username, password="wrong")
        assert resp.status_code == 200
    # The 11th attempt is throttled.
    resp = login(client, user_a.username, password="wrong")
    assert resp.status_code == 429


def test_registration_disabled_returns_403(client, monkeypatch):
    monkeypatch.setattr(Config, "REGISTRATION_ENABLED", False)
    resp = client.post(
        "/register",
        data={"username": "newbie", "password": "abcdef", "confirm_password": "abcdef"},
    )
    assert resp.status_code == 403


def test_registration_enabled_creates_account(client, monkeypatch):
    monkeypatch.setattr(Config, "REGISTRATION_ENABLED", True)
    resp = client.post(
        "/register",
        data={"username": "brandnew_user", "password": "abcdef", "confirm_password": "abcdef"},
        follow_redirects=False,
    )
    # Successful registration logs in and redirects to the dashboard.
    assert resp.status_code == 302


def test_registration_rate_limited(client, monkeypatch):
    monkeypatch.setattr(Config, "REGISTRATION_ENABLED", True)
    # 3 registrations per IP per hour are allowed; the 4th is throttled.
    for i in range(3):
        client.post(
            "/register",
            data={"username": f"rl_user_{i}", "password": "abcdef", "confirm_password": "abcdef"},
        )
        client.get("/logout")
    resp = client.post(
        "/register",
        data={"username": "rl_user_over", "password": "abcdef", "confirm_password": "abcdef"},
    )
    assert resp.status_code == 429
