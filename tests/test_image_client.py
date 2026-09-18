"""app.services.image_client — EXIF extraction plus (this phase) optional
TinEye reverse image search, gated independently from Google Vision."""
from types import SimpleNamespace
from unittest.mock import patch
from app.services import image_client


def _cfg(enabled=True, api_key="fake-key", base_url=None):
    return SimpleNamespace(is_enabled=enabled, api_key=api_key, base_url=base_url)


def test_analyze_image_not_configured_by_default(synthetic_image):
    with patch.object(image_client, "get_by_service", return_value=None):
        result = image_client.analyze_image(synthetic_image)

    assert result["reverse_image_search"]["status"] == "not_configured"
    assert result["reverse_image_search"]["matches"] == []


def test_analyze_image_tineye_success(synthetic_image):
    def fake_get_by_service(name):
        if name == "TinEye":
            return _cfg()
        return None

    fake_response = {"status": "ok", "match_count": 2, "matches": [{"url": "https://a.example", "score": 90}]}

    with patch.object(image_client, "get_by_service", side_effect=fake_get_by_service), \
         patch.object(image_client, "_call_tineye", return_value=fake_response):
        result = image_client.analyze_image(synthetic_image)

    assert result["reverse_image_search"]["status"] == "ok"
    assert result["reverse_image_search"]["match_count"] == 2
    assert result["reverse_image_search"]["matches"][0]["url"] == "https://a.example"


def test_analyze_image_tineye_disabled_stays_not_configured(synthetic_image):
    def fake_get_by_service(name):
        if name == "TinEye":
            return _cfg(enabled=False)
        return None

    with patch.object(image_client, "get_by_service", side_effect=fake_get_by_service):
        result = image_client.analyze_image(synthetic_image)

    assert result["reverse_image_search"]["status"] == "not_configured"


def test_analyze_image_tineye_401_friendly_message(synthetic_image):
    import httpx

    def fake_get_by_service(name):
        if name == "TinEye":
            return _cfg()
        return None

    request = httpx.Request("POST", "https://api.tineye.com/rest/search/")
    response = httpx.Response(401, request=request)
    error = httpx.HTTPStatusError("unauthorized", request=request, response=response)

    with patch.object(image_client, "get_by_service", side_effect=fake_get_by_service), \
         patch.object(image_client, "_call_tineye", side_effect=error):
        result = image_client.analyze_image(synthetic_image)

    assert result["reverse_image_search"]["status"] == "api_error"
    assert "401" in result["reverse_image_search"]["error"]
    assert "unauthorized" not in result["reverse_image_search"]["error"].lower()


def test_analyze_image_tineye_generic_failure_does_not_raise(synthetic_image):
    def fake_get_by_service(name):
        if name == "TinEye":
            return _cfg()
        return None

    with patch.object(image_client, "get_by_service", side_effect=fake_get_by_service), \
         patch.object(image_client, "_call_tineye", side_effect=RuntimeError("boom")):
        result = image_client.analyze_image(synthetic_image)  # must not raise

    assert result["reverse_image_search"]["status"] == "api_error"
    assert result["reverse_image_search"]["matches"] == []


def test_analyze_image_still_extracts_exif_regardless_of_tineye(synthetic_image):
    with patch.object(image_client, "get_by_service", return_value=None):
        result = image_client.analyze_image(synthetic_image)

    assert result["exif"]["Width"] == "32"
    assert result["exif"]["Height"] == "32"
