"""Integration: /investigate/image route renders the TinEye reverse-image
search block that app.services.image_client now returns."""
import io
from unittest.mock import patch
from tests.conftest import login


def _upload(client, case_of_a):
    fake_result = {
        "identified_person": "Metadata extracted (no API configured)",
        "confidence": "N/A",
        "emails": [],
        "social_profiles": [],
        "media_mentions": [],
        "recent_posts": [],
        "exif": {"Width": "32", "Height": "32"},
        "reverse_image_search": {
            "status": "ok",
            "match_count": 1,
            "matches": [{"url": "https://match.example/photo", "score": 88}],
        },
    }
    with patch("app.services.image_client.analyze_image", return_value=fake_result):
        resp = client.post(
            "/investigate/image",
            data={
                "image": (io.BytesIO(b"\x89PNG\r\n\x1a\nfake"), "test.png"),
                "case_id": case_of_a.id,
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    return resp


def test_image_route_renders_tineye_matches(app, client, user_a, case_of_a):
    login(client, user_a.username)
    resp = _upload(client, case_of_a)

    assert resp.status_code == 200
    assert b"match.example/photo" in resp.data
    assert b"1 match" in resp.data


def test_image_route_shows_not_configured_message(app, client, user_a, case_of_a):
    login(client, user_a.username)
    fake_result = {
        "identified_person": "Metadata extracted (no API configured)",
        "confidence": "N/A",
        "emails": [], "social_profiles": [], "media_mentions": [], "recent_posts": [],
        "exif": {},
        "reverse_image_search": {"status": "not_configured", "matches": []},
    }
    with patch("app.services.image_client.analyze_image", return_value=fake_result):
        resp = client.post(
            "/investigate/image",
            data={"image": (io.BytesIO(b"\x89PNG\r\n\x1a\nfake"), "test.png"), "case_id": case_of_a.id},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

    assert resp.status_code == 200
    assert b"requires a paid account" in resp.data
