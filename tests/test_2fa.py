"""TOTP two-factor authentication: settings enable/disable/regenerate flow,
and the login-time second-factor challenge."""
import re
import pyotp
from tests.conftest import login, login_with_2fa
from app.repositories.user_repository import get_by_id


def _enable_2fa(app, client, user) -> str:
    """Drive the real enable flow (GET /settings/2fa -> POST .../confirm)
    and return the raw TOTP secret for generating codes in later steps."""
    login(client, user.username)
    resp = client.get("/settings/2fa")
    m = re.search(rb'Manual key: <code[^>]*>([A-Z0-9]+)</code>', resp.data)
    secret = m.group(1).decode()
    confirm = client.post("/settings/2fa/confirm", data={"code": pyotp.TOTP(secret).now()})
    assert confirm.status_code == 200
    client.get("/logout")
    return secret


def test_enable_shows_qr_and_manual_secret(app, client, user_a):
    login(client, user_a.username)
    resp = client.get("/settings/2fa")
    assert resp.status_code == 200
    assert b"qr code" in resp.data.lower() or b"QR code" in resp.data
    assert b"Manual key" in resp.data


def test_confirm_with_wrong_code_does_not_enable(app, client, user_a):
    login(client, user_a.username)
    client.get("/settings/2fa")  # generates + persists the pending secret
    resp = client.post("/settings/2fa/confirm", data={"code": "000000"}, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert get_by_id(user_a.id).totp_enabled is False


def test_confirm_with_correct_code_enables_and_shows_recovery_codes(app, client, user_a):
    login(client, user_a.username)
    resp = client.get("/settings/2fa")
    m = re.search(rb'Manual key: <code[^>]*>([A-Z0-9]+)</code>', resp.data)
    secret = m.group(1).decode()

    confirm = client.post("/settings/2fa/confirm", data={"code": pyotp.TOTP(secret).now()},
                           follow_redirects=True)
    assert confirm.status_code == 200
    assert b"Recovery Codes" in confirm.data
    assert re.search(rb'[a-f0-9]{4}-[a-f0-9]{4}', confirm.data)
    with app.app_context():
        assert get_by_id(user_a.id).totp_enabled is True


def test_login_redirects_to_verify_2fa_when_enabled(app, client, user_a):
    secret = _enable_2fa(app, client, user_a)
    resp = login(client, user_a.username)
    assert resp.status_code == 302
    assert "/login/verify-2fa" in resp.headers.get("Location", "")


def test_login_correct_totp_code_succeeds(app, client, user_a):
    secret = _enable_2fa(app, client, user_a)
    resp = login_with_2fa(client, user_a.username, secret)
    assert resp.status_code == 302
    assert "/login" not in resp.headers.get("Location", "")


def test_login_wrong_totp_code_rejected(app, client, user_a):
    _enable_2fa(app, client, user_a)
    login(client, user_a.username)
    resp = client.post("/login/verify-2fa", data={"code": "000000"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Invalid code" in resp.data


def test_login_2fa_rate_limited(app, client, user_a):
    _enable_2fa(app, client, user_a)
    login(client, user_a.username)
    statuses = [
        client.post("/login/verify-2fa", data={"code": "000000"}).status_code
        for _ in range(7)
    ]
    assert 429 in statuses


def test_recovery_code_logs_in_and_is_one_time_use(app, client, user_a):
    login(client, user_a.username)
    resp = client.get("/settings/2fa")
    m = re.search(rb'Manual key: <code[^>]*>([A-Z0-9]+)</code>', resp.data)
    secret = m.group(1).decode()
    confirm = client.post("/settings/2fa/confirm", data={"code": pyotp.TOTP(secret).now()},
                           follow_redirects=True)
    recovery_code = re.search(rb'([a-f0-9]{4}-[a-f0-9]{4})', confirm.data).group(1).decode()
    client.get("/logout")

    login(client, user_a.username)
    resp = client.post("/login/verify-2fa", data={"code": recovery_code}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Invalid code" not in resp.data
    client.get("/logout")

    # second use of the same code must fail
    login(client, user_a.username)
    resp = client.post("/login/verify-2fa", data={"code": recovery_code}, follow_redirects=True)
    assert b"Invalid code" in resp.data


def test_disable_requires_correct_password(app, client, user_a):
    from tests.conftest import PASSWORD
    secret = _enable_2fa(app, client, user_a)
    login_with_2fa(client, user_a.username, secret)

    resp = client.post("/settings/2fa/disable", data={"password": "wrong-password"}, follow_redirects=True)
    assert b"Incorrect password" in resp.data
    with app.app_context():
        assert get_by_id(user_a.id).totp_enabled is True

    resp = client.post("/settings/2fa/disable", data={"password": PASSWORD}, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        u = get_by_id(user_a.id)
        assert u.totp_enabled is False
        assert u.totp_secret is None


def test_regenerate_recovery_codes_invalidates_old_ones(app, client, user_a):
    login(client, user_a.username)
    resp = client.get("/settings/2fa")
    m = re.search(rb'Manual key: <code[^>]*>([A-Z0-9]+)</code>', resp.data)
    secret = m.group(1).decode()
    confirm = client.post("/settings/2fa/confirm", data={"code": pyotp.TOTP(secret).now()},
                           follow_redirects=True)
    old_code = re.search(rb'([a-f0-9]{4}-[a-f0-9]{4})', confirm.data).group(1).decode()

    regen = client.post("/settings/2fa/regenerate-codes", follow_redirects=True)
    assert regen.status_code == 200
    new_code = re.search(rb'([a-f0-9]{4}-[a-f0-9]{4})', regen.data).group(1).decode()
    client.get("/logout")

    login(client, user_a.username)
    resp = client.post("/login/verify-2fa", data={"code": old_code}, follow_redirects=True)
    assert b"Invalid code" in resp.data
    client.get("/logout")

    login(client, user_a.username)
    resp = client.post("/login/verify-2fa", data={"code": new_code}, follow_redirects=True)
    assert b"Invalid code" not in resp.data


def test_non_2fa_user_login_unaffected(client, user_b):
    """A user without 2FA enabled must log in immediately — no
    pending_2fa session state, no redirect to verify-2fa."""
    resp = login(client, user_b.username)
    assert resp.status_code == 302
    assert "verify-2fa" not in resp.headers.get("Location", "")
