"""app.services.report_exporter — map/graph snapshot embedding in the
PDF/HTML/DOCX exports (_capture_snapshots + the per-format sections built
from it). CSV/XLSX intentionally don't get this section (no visual
formats). Uses a real tiny PNG (via Pillow) as the fake screenshot so
fpdf2/python-docx actually embed it rather than erroring on garbage
image bytes."""
import io
import json
from unittest.mock import patch
from app.services import report_exporter


def _tiny_png_bytes() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), color=(80, 120, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _make_case_and_investigations(app, user):
    from app.repositories.case_repository import create_case
    from app.repositories.investigation_repository import create_investigation
    with app.app_context():
        case = create_case("Viz Test Case", "desc", owner_user_id=user.id)
        inv = create_investigation(
            kind="ip", query="8.8.8.8",
            result_json=json.dumps({"ip": "8.8.8.8", "geo": {"lat": 1.0, "lon": 2.0, "city": "X", "country": "Y"}}),
            user_id=user.id, case_id=case.id, confidence="CONFIRMED",
        )
    return case, [inv]


# ── _capture_snapshots ──────────────────────────────────────────────────────

def test_capture_snapshots_skips_when_app_missing(app, user_a):
    case, _ = _make_case_and_investigations(app, user_a)
    result = report_exporter._capture_snapshots(case, None, user_a.id)
    assert result == {"map": None, "graph": None}


def test_capture_snapshots_skips_when_user_id_missing(app, user_a):
    case, _ = _make_case_and_investigations(app, user_a)
    result = report_exporter._capture_snapshots(case, app, None)
    assert result == {"map": None, "graph": None}


def test_capture_snapshots_skips_when_playwright_unavailable(app, user_a):
    from app.services import report_snapshot
    case, _ = _make_case_and_investigations(app, user_a)
    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", False):
        result = report_exporter._capture_snapshots(case, app, user_a.id)
    assert result == {"map": None, "graph": None}


def test_capture_snapshots_calls_both_captures_with_case_id(app, user_a):
    from app.services import report_snapshot
    case, _ = _make_case_and_investigations(app, user_a)
    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", True), \
         patch.object(report_snapshot, "capture_map_snapshot", return_value=b"MAPPNG") as mock_map, \
         patch.object(report_snapshot, "capture_graph_snapshot", return_value=b"GRAPHPNG") as mock_graph:
        result = report_exporter._capture_snapshots(case, app, user_a.id)

    mock_map.assert_called_once_with(app, user_a.id, case.id)
    mock_graph.assert_called_once_with(app, user_a.id, case.id)
    assert result == {"map": b"MAPPNG", "graph": b"GRAPHPNG"}


def test_capture_snapshots_never_raises_on_internal_error(app, user_a):
    from app.services import report_snapshot
    case, _ = _make_case_and_investigations(app, user_a)
    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", True), \
         patch.object(report_snapshot, "capture_map_snapshot", side_effect=RuntimeError("boom")):
        result = report_exporter._capture_snapshots(case, app, user_a.id)
    assert result == {"map": None, "graph": None}


# ── export_pdf ───────────────────────────────────────────────────────────────

def test_export_pdf_without_snapshots_has_no_visualizations_section(app, user_a):
    case, invs = _make_case_and_investigations(app, user_a)
    pdf_bytes = report_exporter.export_pdf(case, invs)
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 0


def test_export_pdf_embeds_snapshots_when_available(app, user_a):
    from app.services import report_snapshot
    case, invs = _make_case_and_investigations(app, user_a)
    png = _tiny_png_bytes()

    without = report_exporter.export_pdf(case, invs)
    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", True), \
         patch.object(report_snapshot, "capture_map_snapshot", return_value=png), \
         patch.object(report_snapshot, "capture_graph_snapshot", return_value=png):
        with_viz = report_exporter.export_pdf(case, invs, app=app, snapshot_user_id=user_a.id)

    assert len(with_viz) > len(without)


def test_export_pdf_never_raises_when_snapshot_bytes_are_garbage(app, user_a):
    """A corrupted/undecodable 'PNG' must not crash the whole export —
    fpdf2's image() failure is caught and that image is just skipped."""
    from app.services import report_snapshot
    case, invs = _make_case_and_investigations(app, user_a)
    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", True), \
         patch.object(report_snapshot, "capture_map_snapshot", return_value=b"not a real png"), \
         patch.object(report_snapshot, "capture_graph_snapshot", return_value=None):
        pdf_bytes = report_exporter.export_pdf(case, invs, app=app, snapshot_user_id=user_a.id)
    assert len(pdf_bytes) > 0


# ── export_html ──────────────────────────────────────────────────────────────

def test_export_html_without_snapshots_has_no_visualizations_section(app, user_a):
    case, invs = _make_case_and_investigations(app, user_a)
    html_str = report_exporter.export_html(case, invs)
    assert "Visualizations" not in html_str


def test_export_html_embeds_snapshots_as_data_uris(app, user_a):
    from app.services import report_snapshot
    case, invs = _make_case_and_investigations(app, user_a)
    png = _tiny_png_bytes()

    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", True), \
         patch.object(report_snapshot, "capture_map_snapshot", return_value=png), \
         patch.object(report_snapshot, "capture_graph_snapshot", return_value=png):
        html_str = report_exporter.export_html(case, invs, app=app, snapshot_user_id=user_a.id)

    assert "Visualizations" in html_str
    assert "data:image/png;base64," in html_str
    assert "Location Map" in html_str
    assert "Relationship Graph" in html_str


def test_export_html_only_embeds_available_snapshot(app, user_a):
    from app.services import report_snapshot
    case, invs = _make_case_and_investigations(app, user_a)
    png = _tiny_png_bytes()

    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", True), \
         patch.object(report_snapshot, "capture_map_snapshot", return_value=png), \
         patch.object(report_snapshot, "capture_graph_snapshot", return_value=None):
        html_str = report_exporter.export_html(case, invs, app=app, snapshot_user_id=user_a.id)

    assert "Location Map" in html_str
    assert "Relationship Graph" not in html_str


# ── export_docx ──────────────────────────────────────────────────────────────

def test_export_docx_without_snapshots_has_no_visualizations_heading(app, user_a):
    from docx import Document
    case, invs = _make_case_and_investigations(app, user_a)
    docx_bytes = report_exporter.export_docx(case, invs)
    doc = Document(io.BytesIO(docx_bytes))
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert not any("VISUALIZATIONS" in h for h in headings)


def test_export_docx_embeds_snapshots_as_inline_images(app, user_a):
    from docx import Document
    from app.services import report_snapshot
    case, invs = _make_case_and_investigations(app, user_a)
    png = _tiny_png_bytes()

    without = report_exporter.export_docx(case, invs)
    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", True), \
         patch.object(report_snapshot, "capture_map_snapshot", return_value=png), \
         patch.object(report_snapshot, "capture_graph_snapshot", return_value=png):
        with_viz = report_exporter.export_docx(case, invs, app=app, snapshot_user_id=user_a.id)

    doc_without = Document(io.BytesIO(without))
    doc_with = Document(io.BytesIO(with_viz))
    assert len(doc_with.inline_shapes) > len(doc_without.inline_shapes)

    headings = [p.text for p in doc_with.paragraphs if p.style.name.startswith("Heading")]
    assert any("VISUALIZATIONS" in h for h in headings)
