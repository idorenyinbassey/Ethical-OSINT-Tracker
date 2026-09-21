"""app.services.ai_client — local (Ollama) and cloud (Gemini) AI backends
for case analysis/strategy suggestions and report-summary drafting.

Neither backend is independently verified against live traffic — this
sandbox has no Ollama install to test against and blocks
generativelanguage.googleapis.com outright — so every test here mocks the
HTTP layer, following the same _FakeClient/_FakeResponse convention
already used in tests/test_hibp_client.py and tests/test_paste_client.py.
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

from app.services import ai_client


def _cfg(enabled=True, api_key=None, base_url=None, notes=""):
    return SimpleNamespace(is_enabled=enabled, api_key=api_key, base_url=base_url, notes=notes)


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json


class _FakeClient:
    def __init__(self, impl):
        self._impl = impl

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, **kwargs):
        return self._impl(url, **kwargs)


def _client_factory(impl):
    def factory(timeout=60.0):
        return _FakeClient(impl)
    return factory


# ── is_local_available_by_config() / is_cloud_configured() ──────────────────

def test_local_available_with_no_config_row():
    with patch.object(ai_client, "get_by_service", return_value=None):
        assert ai_client.is_local_available_by_config() is True


def test_local_unavailable_when_explicitly_disabled():
    with patch.object(ai_client, "get_by_service", return_value=_cfg(enabled=False)):
        assert ai_client.is_local_available_by_config() is False


def test_cloud_not_configured_with_no_row():
    with patch.object(ai_client, "get_by_service", return_value=None):
        assert ai_client.is_cloud_configured() is False


def test_cloud_not_configured_without_api_key():
    with patch.object(ai_client, "get_by_service", return_value=_cfg(api_key=None)):
        assert ai_client.is_cloud_configured() is False


def test_cloud_configured_with_enabled_key():
    with patch.object(ai_client, "get_by_service", return_value=_cfg(api_key="secret")):
        assert ai_client.is_cloud_configured() is True


# ── run_local() ───────────────────────────────────────────────────────────

def test_run_local_returns_text_on_success():
    def impl(url, **kwargs):
        assert url == ai_client._OLLAMA_URL
        assert kwargs["json"]["model"] == ai_client._OLLAMA_DEFAULT_MODEL
        return _FakeResponse({"response": "  here is the analysis  "})

    with patch.object(ai_client, "get_by_service", return_value=None), \
         patch.object(ai_client, "get_http_client", _client_factory(impl)):
        result = ai_client.run_local("some prompt")

    assert result["ok"] is True
    assert result["text"] == "here is the analysis"
    assert "llama3.2" in result["source"]


def test_run_local_uses_notes_as_model_override():
    def impl(url, **kwargs):
        assert kwargs["json"]["model"] == "mistral"
        return _FakeResponse({"response": "ok"})

    with patch.object(ai_client, "get_by_service", return_value=_cfg(notes="mistral")), \
         patch.object(ai_client, "get_http_client", _client_factory(impl)):
        result = ai_client.run_local("prompt")

    assert result["ok"] is True
    assert "mistral" in result["source"]


def test_run_local_returns_actionable_error_when_unreachable():
    def impl(url, **kwargs):
        raise ConnectionError("connection refused")

    with patch.object(ai_client, "get_by_service", return_value=None), \
         patch.object(ai_client, "get_http_client", _client_factory(impl)):
        result = ai_client.run_local("prompt")

    assert result["ok"] is False
    assert "Ollama" in result["error"]


def test_run_local_disabled_never_makes_a_request():
    with patch.object(ai_client, "get_by_service", return_value=_cfg(enabled=False)), \
         patch.object(ai_client, "get_http_client") as mock_client:
        result = ai_client.run_local("prompt")

    assert result["ok"] is False
    mock_client.assert_not_called()


def test_run_local_empty_response_is_an_error():
    with patch.object(ai_client, "get_by_service", return_value=None), \
         patch.object(ai_client, "get_http_client", _client_factory(lambda url, **kw: _FakeResponse({"response": ""}))):
        result = ai_client.run_local("prompt")

    assert result["ok"] is False
    assert "no text" in result["error"]


# ── run_cloud() ───────────────────────────────────────────────────────────

def test_run_cloud_not_configured_never_makes_a_request():
    with patch.object(ai_client, "get_by_service", return_value=None), \
         patch.object(ai_client, "get_http_client") as mock_client:
        result = ai_client.run_cloud("prompt")

    assert result["ok"] is False
    mock_client.assert_not_called()


def test_run_cloud_returns_text_on_success():
    def impl(url, **kwargs):
        assert url == f"{ai_client._GEMINI_DEFAULT_BASE_URL}/v1beta/models/{ai_client._GEMINI_DEFAULT_MODEL}:generateContent"
        assert kwargs["params"] == {"key": "secret-key"}
        assert kwargs["json"]["contents"][0]["parts"][0]["text"] == "prompt text"
        return _FakeResponse({"candidates": [{"content": {"parts": [{"text": " analysis "}]}}]})

    with patch.object(ai_client, "get_by_service", return_value=_cfg(api_key="secret-key")), \
         patch.object(ai_client, "get_http_client", _client_factory(impl)):
        result = ai_client.run_cloud("prompt text")

    assert result["ok"] is True
    assert result["text"] == "analysis"


def test_run_cloud_uses_notes_as_model_override():
    def impl(url, **kwargs):
        assert "custom-model" in url
        return _FakeResponse({"candidates": [{"content": {"parts": [{"text": "x"}]}}]})

    with patch.object(ai_client, "get_by_service", return_value=_cfg(api_key="k", notes="custom-model")), \
         patch.object(ai_client, "get_http_client", _client_factory(impl)):
        result = ai_client.run_cloud("prompt")

    assert result["ok"] is True


def test_run_cloud_unexpected_shape_is_a_clear_error():
    with patch.object(ai_client, "get_by_service", return_value=_cfg(api_key="k")), \
         patch.object(ai_client, "get_http_client", _client_factory(lambda url, **kw: _FakeResponse({"unexpected": True}))):
        result = ai_client.run_cloud("prompt")

    assert result["ok"] is False
    assert "unexpected response shape" in result["error"]


def test_run_cloud_request_failure_is_reported():
    def impl(url, **kwargs):
        raise ConnectionError("network down")

    with patch.object(ai_client, "get_by_service", return_value=_cfg(api_key="k")), \
         patch.object(ai_client, "get_http_client", _client_factory(impl)):
        result = ai_client.run_cloud("prompt")

    assert result["ok"] is False
    assert "Gemini" in result["error"]


# ── build_case_digest() / analyze_case() ─────────────────────────────────────

def _make_case_with_investigation(app, user):
    from app.repositories.case_repository import create_case
    from app.repositories.investigation_repository import create_investigation
    with app.app_context():
        case = create_case("AI Digest Test Case", "a test case", owner_user_id=user.id)
        inv = create_investigation(
            kind="domain", query="example.com",
            result_json=json.dumps({"domain": "example.com"}),
            user_id=user.id, case_id=case.id, confidence="CONFIRMED",
        )
    return case, [inv]


def test_build_case_digest_includes_investigations_notes_and_comments(app, user_a):
    from app.repositories.case_comment_repository import add_comment
    from app.repositories.case_note_repository import add_note

    case, invs = _make_case_with_investigation(app, user_a)
    with app.app_context():
        add_comment(case.id, user_a.id, user_a.username, "A team comment.")
        add_note(case.id, user_a.id, user_a.username, "lead", "A journal entry.")
        from app.repositories.case_comment_repository import list_comments
        from app.repositories.case_note_repository import list_notes
        comments = list_comments(case.id)
        notes = list_notes(case.id)
        digest = ai_client.build_case_digest(case, invs, comments, notes)

    assert "AI Digest Test Case" in digest
    assert "example.com" in digest
    assert "A team comment." in digest
    assert "A journal entry." in digest


def test_analyze_case_routes_to_local_backend_with_strategy_prompt(app, user_a):
    case, invs = _make_case_with_investigation(app, user_a)
    with app.app_context(), \
         patch.object(ai_client, "run_local", return_value={"ok": True, "text": "x", "source": "local"}) as mock_local, \
         patch.object(ai_client, "run_cloud") as mock_cloud:
        ai_client.analyze_case(case, invs, [], [], backend="local", analysis_type="strategy")

    mock_local.assert_called_once()
    mock_cloud.assert_not_called()
    assert "next investigative steps" in mock_local.call_args[0][0]


def test_analyze_case_routes_to_cloud_backend_with_summary_prompt(app, user_a):
    case, invs = _make_case_with_investigation(app, user_a)
    with app.app_context(), \
         patch.object(ai_client, "run_cloud", return_value={"ok": True, "text": "x", "source": "cloud"}) as mock_cloud, \
         patch.object(ai_client, "run_local") as mock_local:
        ai_client.analyze_case(case, invs, [], [], backend="cloud", analysis_type="summary")

    mock_cloud.assert_called_once()
    mock_local.assert_not_called()
    assert "executive summary" in mock_cloud.call_args[0][0]
