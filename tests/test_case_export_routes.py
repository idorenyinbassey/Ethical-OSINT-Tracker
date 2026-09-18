"""app.routes.cases export routes — verifies the PDF/DOCX/HTML export
routes (both the synchronous ones and the async job) now pass `app` and
`snapshot_user_id` through to report_exporter so map/graph snapshots can
be embedded. Mocks report_exporter itself so no real PDF/DOCX rendering
or headless browser work happens here."""
import time
from unittest.mock import patch
from tests.conftest import login


def test_export_pdf_route_passes_app_and_user_id(app, client, user_a, case_of_a):
    login(client, user_a.username)
    with patch("app.services.report_exporter.export_pdf", return_value=b"%PDF-fake") as mock_export:
        resp = client.get(f"/cases/{case_of_a.id}/export/pdf")

    assert resp.status_code == 200
    _, kwargs = mock_export.call_args
    assert kwargs["app"] is app
    assert kwargs["snapshot_user_id"] == user_a.id


def test_export_docx_route_passes_app_and_user_id(app, client, user_a, case_of_a):
    login(client, user_a.username)
    with patch("app.services.report_exporter.export_docx", return_value=b"PK-fake-docx") as mock_export:
        resp = client.get(f"/cases/{case_of_a.id}/export/docx")

    assert resp.status_code == 200
    _, kwargs = mock_export.call_args
    assert kwargs["app"] is app
    assert kwargs["snapshot_user_id"] == user_a.id


def test_export_html_route_passes_app_and_user_id(app, client, user_a, case_of_a):
    login(client, user_a.username)
    with patch("app.services.report_exporter.export_html", return_value="<html>fake</html>") as mock_export:
        resp = client.get(f"/cases/{case_of_a.id}/export/html")

    assert resp.status_code == 200
    _, kwargs = mock_export.call_args
    assert kwargs["app"] is app
    assert kwargs["snapshot_user_id"] == user_a.id


def test_export_start_async_job_passes_app_and_user_id(app, client, user_a, case_of_a):
    login(client, user_a.username)
    with patch("app.services.report_exporter.export_pdf", return_value=b"%PDF-fake") as mock_export:
        resp = client.post(f"/cases/{case_of_a.id}/export/start", data={"fmt": "pdf"})
        assert resp.status_code == 200
        job_id = resp.get_json()["job_id"]

        for _ in range(50):
            status_resp = client.get(f"/cases/export/status/{job_id}")
            if status_resp.get_json().get("status") != "running":
                break
            time.sleep(0.05)

    assert mock_export.called
    _, kwargs = mock_export.call_args
    assert kwargs["app"] is app
    assert kwargs["snapshot_user_id"] == user_a.id
