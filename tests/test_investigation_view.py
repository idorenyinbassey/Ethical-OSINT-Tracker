"""app.routes.cases.view_investigation() — lets an investigator open a past
scan (while its case still exists) and read its stored fields, so values
found in one tool's result (an email, a domain, a linked profile) can be
copied into a follow-up scan with another tool."""
import json

from tests.conftest import login


def _seed_investigation(app, user_id, case_id, result):
    from app.repositories.investigation_repository import create_investigation
    with app.app_context():
        return create_investigation(
            kind="social", query="johndoe", result_json=json.dumps(result),
            user_id=user_id, case_id=case_id, confidence="CONFIRMED",
        )


def test_view_investigation_shows_nested_fields(app, client, user_a, case_of_a):
    login(client, user_a.username)
    result = {
        "username": "johndoe",
        "results": [
            {"site": "GitHub", "found": True, "email": "johndoe@example.com"},
        ],
    }
    inv = _seed_investigation(app, user_a.id, case_of_a.id, result)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "johndoe@example.com" in body
    assert "GitHub" in body


def test_view_investigation_denies_user_without_case_access(app, client, user_a, user_b, case_of_a):
    inv = _seed_investigation(app, user_a.id, case_of_a.id, {"v": 1})
    login(client, user_b.username)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    assert resp.status_code == 403


def test_view_investigation_rejects_mismatched_case_id(app, client, user_a, case_of_a):
    """An investigation belonging to a DIFFERENT case must 404 even when
    the requester has read access to the case_id in the URL — otherwise a
    user could view any investigation on the site just by guessing its id
    while supplying one of their own case ids."""
    from app.repositories.case_repository import create_case

    with app.app_context():
        other_case = create_case("Other Case", "", owner_user_id=user_a.id)
    inv = _seed_investigation(app, user_a.id, other_case.id, {"v": 1})

    login(client, user_a.username)
    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    assert resp.status_code == 404


def test_view_investigation_handles_malformed_result_json(app, client, user_a, case_of_a):
    from app.repositories.investigation_repository import create_investigation

    login(client, user_a.username)
    with app.app_context():
        inv = create_investigation(
            kind="ip", query="8.8.8.8", result_json="{not valid json",
            user_id=user_a.id, case_id=case_of_a.id,
        )

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    assert resp.status_code == 200
    assert b"Could not read" in resp.data


def test_view_investigation_handles_empty_result(app, client, user_a, case_of_a):
    from app.repositories.investigation_repository import create_investigation

    login(client, user_a.username)
    with app.app_context():
        inv = create_investigation(
            kind="ip", query="8.8.8.8", result_json="",
            user_id=user_a.id, case_id=case_of_a.id,
        )

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    assert resp.status_code == 200
    assert b"no stored result" in resp.data


def test_view_investigation_nonexistent_returns_404(app, client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.get(f"/cases/{case_of_a.id}/investigations/999999")
    assert resp.status_code == 404


# ── Image thumbnails ────────────────────────────────────────────────────────

def test_view_investigation_renders_image_url_as_thumbnail(app, client, user_a, case_of_a):
    login(client, user_a.username)
    result = {"avatar": "https://example.com/profile.jpg", "name": "not-an-image"}
    inv = _seed_investigation(app, user_a.id, case_of_a.id, result)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    body = resp.data.decode()
    assert '<img src="https://example.com/profile.jpg"' in body
    # A plain non-image string must not get an <img> tag.
    assert '<img src="not-an-image"' not in body


def test_view_investigation_renders_extensionless_avatar_url_as_thumbnail(app, client, user_a, case_of_a):
    """GitHub/Gravatar-style avatar URLs carry no file extension at all
    (e.g. https://avatars.githubusercontent.com/u/1?v=4) — the field
    name (avatar/photo/thumbnail/...) is what should trigger a thumbnail
    here, not the URL shape alone."""
    login(client, user_a.username)
    avatar_url = "https://avatars.githubusercontent.com/u/1?v=4"
    result = {"avatar": avatar_url, "unrelated_url": "https://example.com/page?v=4"}
    inv = _seed_investigation(app, user_a.id, case_of_a.id, result)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    body = resp.data.decode()
    assert f'<img src="{avatar_url}"' in body
    # A same-shaped URL under an unrelated key must NOT get a thumbnail.
    assert '<img src="https://example.com/page?v=4"' not in body


def test_view_investigation_renders_data_uri_image_as_thumbnail(app, client, user_a, case_of_a):
    login(client, user_a.username)
    data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
    result = {"thumbnail": data_uri}
    inv = _seed_investigation(app, user_a.id, case_of_a.id, result)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    body = resp.data.decode()
    assert f'<img src="{data_uri}"' in body


def test_view_investigation_does_not_thumbnail_http_image_urls(app, client, user_a, case_of_a):
    """The CSP's img-src only allows 'self', data:, and https: — an
    http:// URL would never actually load as a thumbnail (the browser
    blocks the request), so it must render as plain text instead of a
    guaranteed-broken <img> tag, whether it has an image extension or an
    image-suggesting field name."""
    login(client, user_a.username)
    result = {
        "avatar": "http://example.com/profile.jpg",
        "photo": "http://avatars.example.com/u/1",
    }
    inv = _seed_investigation(app, user_a.id, case_of_a.id, result)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    body = resp.data.decode()
    assert '<img src="http://example.com/profile.jpg"' not in body
    assert '<img src="http://avatars.example.com/u/1"' not in body
    assert "http://example.com/profile.jpg" in body
    assert "http://avatars.example.com/u/1" in body


# ── Verbose sections collapse; short/high-signal ones don't ────────────────

def test_view_investigation_collapses_long_list_of_complex_items(app, client, user_a, case_of_a):
    import re

    login(client, user_a.username)
    result = {
        "username_guesses": ["johndoe", "j.doe", "j_doe", "jdoe"],
        "dork_links": [
            {"label": f"Link {i}", "url": f"https://example.com/{i}"} for i in range(6)
        ],
    }
    inv = _seed_investigation(app, user_a.id, case_of_a.id, result)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    body = resp.data.decode()

    assert "click to expand" in body
    # username_guesses (a short list of plain strings) must render
    # immediately, not hidden behind the same collapse as dork_links.
    first_details = re.search(r"<details.*?</details>", body, re.S)
    assert "johndoe" not in first_details.group(0)
    assert "Link 0" in first_details.group(0)


def test_view_investigation_does_not_collapse_short_plain_list(app, client, user_a, case_of_a):
    login(client, user_a.username)
    result = {"username_guesses": ["johndoe", "j.doe", "j_doe", "jdoe", "doej", "jd"]}
    inv = _seed_investigation(app, user_a.id, case_of_a.id, result)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    body = resp.data.decode()
    assert "click to expand" not in body
    assert "johndoe" in body
