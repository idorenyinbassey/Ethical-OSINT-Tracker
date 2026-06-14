"""Generate PDF and DOCX investigation reports for cases."""
import io
import json
import datetime


def _format_result(result_json: str) -> str:
    try:
        d = json.loads(result_json)
        lines = []
        def flatten(obj, prefix=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    flatten(v, f"{prefix}{k}: " if not prefix else f"{prefix}{k}: ")
            elif isinstance(obj, list):
                for i, item in enumerate(obj[:5]):
                    flatten(item, f"{prefix}[{i}] ")
            else:
                lines.append(f"{prefix}{str(obj)[:120]}")
        flatten(d)
        return "\n".join(lines[:30]) or "(no data)"
    except Exception:
        return result_json[:300]


def export_pdf(case, investigations) -> bytes:
    """Return PDF bytes for a case and its investigations."""
    try:
        from fpdf import FPDF
    except ImportError:
        raise RuntimeError("fpdf2 not installed. Run: pip install fpdf2")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(99, 102, 241)  # indigo
    pdf.cell(0, 10, "OSINT Investigation Report", ln=True)

    # Case header
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(4)
    pdf.cell(0, 8, f"Case: {case.title}", ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, f"Status: {case.status.replace('_', ' ').title()}  |  Priority: {case.priority.title()}", ln=True)
    pdf.cell(0, 6, f"Created: {case.created_at.strftime('%Y-%m-%d %H:%M') if case.created_at else 'Unknown'}", ln=True)
    if case.description:
        pdf.multi_cell(0, 6, f"Description: {case.description}")
    pdf.cell(0, 6, f"Report generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC", ln=True)

    pdf.ln(4)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # Investigations
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, f"Investigations ({len(investigations)})", ln=True)

    for inv in investigations:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(60, 60, 60)
        kind_label = inv.kind.replace("_", " ").title()
        pdf.cell(0, 7, f"[{kind_label}]  {inv.query}", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 100, 100)
        if inv.created_at:
            pdf.cell(0, 5, inv.created_at.strftime('%Y-%m-%d %H:%M'), ln=True)
        detail = _format_result(inv.result_json)
        for line in detail.split("\n")[:20]:
            if line.strip():
                pdf.multi_cell(0, 5, "  " + line.strip()[:150])

    return pdf.output()


def export_docx(case, investigations) -> bytes:
    """Return DOCX bytes for a case and its investigations."""
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    heading = doc.add_heading("OSINT Investigation Report", level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.LEFT

    doc.add_heading(f"Case: {case.title}", level=1)

    meta = doc.add_paragraph()
    meta.add_run(f"Status: ").bold = True
    meta.add_run(case.status.replace("_", " ").title() + "\n")
    meta.add_run(f"Priority: ").bold = True
    meta.add_run(case.priority.title() + "\n")
    meta.add_run(f"Created: ").bold = True
    meta.add_run(case.created_at.strftime('%Y-%m-%d %H:%M') if case.created_at else "Unknown")

    if case.description:
        doc.add_paragraph(case.description)

    doc.add_paragraph(f"Report generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")

    doc.add_heading(f"Investigations ({len(investigations)})", level=2)

    for inv in investigations:
        kind_label = inv.kind.replace("_", " ").title()
        h = doc.add_heading(f"{kind_label}: {inv.query}", level=3)
        if inv.created_at:
            doc.add_paragraph(inv.created_at.strftime('%Y-%m-%d %H:%M'), style="Caption")
        detail = _format_result(inv.result_json)
        p = doc.add_paragraph()
        p.add_run(detail).font.size = Pt(8)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
