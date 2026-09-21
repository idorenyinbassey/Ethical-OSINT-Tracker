"""/cases/<id>/analysis — AI-assisted strategy suggestions and report-
summary drafting. A generated result is persisted as a CaseNote
(kind="ai_analysis"), which is why these tests check for a new
Investigator Journal entry rather than a separate AI-specific table."""
from unittest.mock import patch

from tests.conftest import login


def test_analysis_page_loads(app, client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.get(f"/cases/{case_of_a.id}/analysis")
    assert resp.status_code == 200
    assert b"AI Analysis" in resp.data


def test_analysis_page_hides_cloud_option_when_not_configured(app, client, user_a, case_of_a):
    login(client, user_a.username)
    with patch("app.services.ai_client.is_cloud_configured", return_value=False):
        resp = client.get(f"/cases/{case_of_a.id}/analysis")
    assert b"Not configured" in resp.data


def test_local_analysis_success_persists_a_journal_note(app, client, user_a, case_of_a):
    login(client, user_a.username)
    fake_result = {"ok": True, "text": "Suggested next steps: ...", "source": "Local AI (Ollama, llama3.2)"}
    with patch("app.services.ai_client.analyze_case", return_value=fake_result):
        resp = client.post(f"/cases/{case_of_a.id}/analysis",
                            data={"backend": "local", "analysis_type": "strategy"},
                            follow_redirects=True)

    assert resp.status_code == 200
    assert b"Suggested next steps" in resp.data
    assert b"AI Analysis" in resp.data

    with app.app_context():
        from app.repositories.case_note_repository import list_notes
        notes = list_notes(case_of_a.id)
    ai_notes = [n for n in notes if n.kind == "ai_analysis"]
    assert len(ai_notes) == 1
    assert "Suggested next steps" in ai_notes[0].body


def test_local_analysis_failure_does_not_persist_a_note(app, client, user_a, case_of_a):
    login(client, user_a.username)
    fake_result = {"ok": False, "text": None, "source": "", "error": "Ollama unreachable"}
    with patch("app.services.ai_client.analyze_case", return_value=fake_result):
        resp = client.post(f"/cases/{case_of_a.id}/analysis",
                            data={"backend": "local", "analysis_type": "strategy"},
                            follow_redirects=True)

    assert resp.status_code == 200
    assert b"Ollama unreachable" in resp.data

    with app.app_context():
        from app.repositories.case_note_repository import list_notes
        notes = list_notes(case_of_a.id)
    assert not any(n.kind == "ai_analysis" for n in notes)


def test_cloud_analysis_rejected_without_config_never_calls_analyze(app, client, user_a, case_of_a):
    login(client, user_a.username)
    with patch("app.services.ai_client.is_cloud_configured", return_value=False), \
         patch("app.services.ai_client.analyze_case") as mock_analyze:
        resp = client.post(f"/cases/{case_of_a.id}/analysis",
                            data={"backend": "cloud", "analysis_type": "strategy"},
                            follow_redirects=True)

    assert resp.status_code == 200
    assert b"not configured" in resp.data.lower()
    mock_analyze.assert_not_called()


def test_analysis_route_requires_login(client, case_of_a):
    resp = client.get(f"/cases/{case_of_a.id}/analysis")
    assert resp.status_code in (302, 401)
