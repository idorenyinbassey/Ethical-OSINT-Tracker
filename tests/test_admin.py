"""Admin user-management: create-user route + authorization."""
from app.repositories.user_repository import get_by_username
from tests.conftest import login


def test_admin_can_create_user(app, client, admin_user):
    login(client, admin_user.username)
    resp = client.post(
        "/admin/users/create",
        data={"username": "created_by_admin", "password": "secret6"},
    )
    assert resp.status_code == 302  # redirect back to the users page
    with app.app_context():
        u = get_by_username("created_by_admin")
        assert u is not None
        assert u.is_admin is False


def test_admin_can_create_admin_user(app, client, admin_user):
    login(client, admin_user.username)
    client.post(
        "/admin/users/create",
        data={"username": "second_admin", "password": "secret6", "is_admin": "on"},
    )
    with app.app_context():
        u = get_by_username("second_admin")
        assert u is not None and u.is_admin is True


def test_non_admin_cannot_create_user(app, client, user_a):
    login(client, user_a.username)
    resp = client.post(
        "/admin/users/create",
        data={"username": "sneaky", "password": "secret6"},
    )
    assert resp.status_code == 403
    with app.app_context():
        assert get_by_username("sneaky") is None


def test_create_rejects_duplicate_username(app, client, admin_user, user_a):
    login(client, admin_user.username)
    resp = client.post(
        "/admin/users/create",
        data={"username": user_a.username, "password": "secret6"},
        follow_redirects=True,
    )
    assert resp.status_code == 200  # redirected back with an error flash, no crash


def test_create_rejects_short_password(app, client, admin_user):
    login(client, admin_user.username)
    client.post(
        "/admin/users/create",
        data={"username": "shortpw_user", "password": "abc"},
    )
    with app.app_context():
        assert get_by_username("shortpw_user") is None
