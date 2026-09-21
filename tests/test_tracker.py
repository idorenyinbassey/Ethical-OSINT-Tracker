"""app.routes.tracker + app.repositories.tracking_repository — Link Tracker
CRUD fixes: an edit route (previously missing entirely), a pause/resume
toggle (previously the only way to stop a link was to delete it, which
also wiped its hit history), hit-list pagination, a real confirmation
step (password re-entry) before delete instead of a bare JS confirm(),
and PUBLIC_BASE_URL support for a link shared through a tunnel/proxy.
"""
import os
from unittest.mock import patch

from tests.conftest import login, PASSWORD


def _create_link_via_route(client, label="Test Link", decoy_mode="404", redirect_url="", case_id=""):
    resp = client.post("/tracker/new", data={
        "label": label, "decoy_mode": decoy_mode,
        "redirect_url": redirect_url, "case_id": case_id,
    }, follow_redirects=False)
    # Redirects to /tracker/<token>
    token = resp.headers["Location"].rsplit("/", 1)[-1]
    return token


# ── Edit ──────────────────────────────────────────────────────────────────

def test_edit_route_renders_prefilled_form(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client, label="Original Label")
    resp = client.get(f"/tracker/{token}/edit")
    assert resp.status_code == 200
    assert b"Original Label" in resp.data


def test_edit_route_updates_the_link(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client, label="Original", decoy_mode="404")
    resp = client.post(f"/tracker/{token}/edit", data={
        "label": "Renamed", "decoy_mode": "blank", "redirect_url": "", "notes": "updated",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Tracking link updated" in resp.data
    assert b"Renamed" in resp.data


def test_edit_route_requires_a_label(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client)
    resp = client.post(f"/tracker/{token}/edit", data={
        "label": "", "decoy_mode": "404", "redirect_url": "", "notes": "",
    }, follow_redirects=True)
    assert b"Label is required" in resp.data


def test_edit_route_rejects_another_users_link(app, client, user_a, user_b):
    login(client, user_a.username)
    token = _create_link_via_route(client)
    client.get("/logout")
    login(client, user_b.username)
    resp = client.get(f"/tracker/{token}/edit")
    assert resp.status_code == 404


# ── Pause / resume ────────────────────────────────────────────────────────

def test_toggle_pauses_and_resumes_a_link(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client)

    resp = client.post(f"/tracker/{token}/toggle", follow_redirects=True)
    assert b"paused" in resp.data.lower()

    with app.app_context():
        from app.repositories.tracking_repository import get_link_by_token
        assert get_link_by_token(token).active is False

    resp = client.post(f"/tracker/{token}/toggle", follow_redirects=True)
    assert b"resumed" in resp.data.lower()
    with app.app_context():
        from app.repositories.tracking_repository import get_link_by_token
        assert get_link_by_token(token).active is True


def test_paused_link_404s_for_visitors_and_records_no_hit(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client)
    client.post(f"/tracker/{token}/toggle")  # pause it

    resp = client.get(f"/t/{token}")
    assert resp.status_code == 404

    with app.app_context():
        from app.repositories.tracking_repository import get_link_by_token, count_hits
        link = get_link_by_token(token)
        assert count_hits(link.id) == 0


def test_paused_link_hit_history_survives_the_pause(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client)
    client.get(f"/t/{token}")  # record one hit while active

    client.post(f"/tracker/{token}/toggle")  # now pause it

    with app.app_context():
        from app.repositories.tracking_repository import get_link_by_token, count_hits
        link = get_link_by_token(token)
        assert count_hits(link.id) == 1  # untouched by pausing


def test_active_link_still_records_hits(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client)
    resp = client.get(f"/t/{token}")
    assert resp.status_code == 200
    with app.app_context():
        from app.repositories.tracking_repository import get_link_by_token, count_hits
        link = get_link_by_token(token)
        assert count_hits(link.id) == 1


# ── Delete now requires the user's own password ─────────────────────────────

def test_delete_rejects_missing_password(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client)
    resp = client.post(f"/tracker/{token}/delete", data={}, follow_redirects=True)
    assert b"Incorrect password" in resp.data
    with app.app_context():
        from app.repositories.tracking_repository import get_link_by_token
        assert get_link_by_token(token) is not None  # not deleted


def test_delete_rejects_wrong_password(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client)
    resp = client.post(f"/tracker/{token}/delete", data={"password": "wrong-password"}, follow_redirects=True)
    assert b"Incorrect password" in resp.data
    with app.app_context():
        from app.repositories.tracking_repository import get_link_by_token
        assert get_link_by_token(token) is not None


def test_delete_succeeds_with_correct_password(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client)
    resp = client.post(f"/tracker/{token}/delete", data={"password": PASSWORD}, follow_redirects=True)
    assert b"Tracking link deleted" in resp.data
    with app.app_context():
        from app.repositories.tracking_repository import get_link_by_token
        assert get_link_by_token(token) is None


# ── Pagination ────────────────────────────────────────────────────────────

def test_list_hits_respects_limit_and_offset(app, user_a, case_of_a):
    from app.repositories.tracking_repository import create_link, record_hit, list_hits
    with app.app_context():
        link = create_link("Paged Link", user_a.id, case_id=case_of_a.id)
        for i in range(5):
            record_hit(link.id, ip=f"1.2.3.{i}")

        newest_two = list_hits(link.id, limit=2, offset=0)
        assert len(newest_two) == 2
        next_two = list_hits(link.id, limit=2, offset=2)
        assert len(next_two) == 2
        assert {h.ip for h in newest_two}.isdisjoint({h.ip for h in next_two})

        everything = list_hits(link.id, limit=None)
        assert len(everything) == 5


def test_detail_route_paginates_and_links_to_next_page(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client)
    with app.app_context():
        from app.repositories.tracking_repository import get_link_by_token, record_hit
        link = get_link_by_token(token)
        for i in range(3):
            record_hit(link.id, ip=f"9.9.9.{i}")

    with patch("app.routes.tracker._HITS_PAGE_SIZE", 2):
        resp = client.get(f"/tracker/{token}")
        assert resp.status_code == 200
        assert b"Older" in resp.data  # more than one page's worth exist

        resp_page2 = client.get(f"/tracker/{token}?page=2")
        assert resp_page2.status_code == 200


# ── PUBLIC_BASE_URL ──────────────────────────────────────────────────────────

def test_tracking_url_uses_public_base_url_when_configured(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client)
    with patch.dict(os.environ, {"PUBLIC_BASE_URL": "https://abc123.ngrok.io"}):
        resp = client.get(f"/tracker/{token}")
    assert b"https://abc123.ngrok.io/t/" in resp.data


def test_tracking_url_falls_back_to_request_host_without_public_base_url(app, client, user_a):
    login(client, user_a.username)
    token = _create_link_via_route(client)
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("PUBLIC_BASE_URL", None)
        resp = client.get(f"/tracker/{token}")
    assert f"/t/{token}".encode() in resp.data
