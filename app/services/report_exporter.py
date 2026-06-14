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


def export_html(case, investigations) -> str:
    """Return a standalone HTML report."""
    import html as _html
    esc = lambda s: _html.escape(str(s) if s is not None else "")
    rows = ""
    for inv in investigations:
        detail = esc(_format_result(inv.result_json)).replace('\n', '<br>')
        ts = inv.created_at.strftime('%Y-%m-%d %H:%M') if inv.created_at else ""
        rows += f"""
        <div class="inv">
          <div class="inv-hd">
            <span class="kind">{esc(inv.kind.replace('_',' ').title())}</span>
            <code class="query">{esc(inv.query)}</code>
            <span class="ts">{ts}</span>
          </div>
          <pre class="detail">{detail}</pre>
        </div>"""
    created = case.created_at.strftime('%Y-%m-%d %H:%M') if case.created_at else "Unknown"
    generated = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    desc_html = f"<p>{esc(case.description)}</p>" if case.description else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>OSINT Report — {esc(case.title)}</title>
<style>
  body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1.5rem;color:#111;background:#fff}}
  h1{{color:#4338ca;margin-bottom:.25rem}}h2{{color:#374151;margin-top:0}}
  .meta{{color:#6b7280;font-size:.875rem;border-bottom:1px solid #e5e7eb;padding-bottom:1rem;margin-bottom:1.5rem}}
  .inv{{border:1px solid #e5e7eb;border-radius:.5rem;margin-bottom:1rem;overflow:hidden}}
  .inv-hd{{background:#f9fafb;padding:.6rem 1rem;display:flex;gap:.75rem;align-items:center;flex-wrap:wrap}}
  .kind{{background:#eef2ff;color:#4338ca;font-size:.7rem;font-weight:600;padding:.2rem .5rem;border-radius:.25rem;white-space:nowrap}}
  .query{{font-size:.875rem;word-break:break-all}}
  .ts{{color:#9ca3af;font-size:.75rem;margin-left:auto;white-space:nowrap}}
  .detail{{margin:0;padding:.75rem 1rem;font-size:.8rem;color:#374151;white-space:pre-wrap;word-break:break-word;background:#fff;border-top:1px solid #f3f4f6}}
</style>
</head>
<body>
<h1>OSINT Investigation Report</h1>
<h2>{esc(case.title)}</h2>
<div class="meta">
  <p>Status: <strong>{esc(case.status.replace('_',' ').title())}</strong> &nbsp;|&nbsp; Priority: <strong>{esc(case.priority.title())}</strong></p>
  <p>Created: {created} &nbsp;|&nbsp; Generated: {generated} UTC &nbsp;|&nbsp; {len(investigations)} investigation(s)</p>
  {desc_html}
</div>
<h3>Investigations ({len(investigations)})</h3>
{rows}
</body>
</html>"""


def export_csv(case, investigations) -> bytes:
    """Return UTF-8 CSV bytes (BOM for Excel compatibility)."""
    import csv
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["OSINT Investigation Report"])
    w.writerow(["Case", case.title])
    w.writerow(["Status", case.status.replace("_", " ").title()])
    w.writerow(["Priority", case.priority.title()])
    w.writerow(["Created", case.created_at.strftime('%Y-%m-%d %H:%M') if case.created_at else ""])
    w.writerow(["Description", case.description or ""])
    w.writerow(["Generated", datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M') + " UTC"])
    w.writerow([])
    w.writerow(["#", "Type", "Query", "Date", "Summary"])
    for i, inv in enumerate(investigations, 1):
        summary = _format_result(inv.result_json).replace('\n', ' | ')[:300]
        ts = inv.created_at.strftime('%Y-%m-%d %H:%M') if inv.created_at else ""
        w.writerow([i, inv.kind.replace("_", " ").title(), inv.query, ts, summary])
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def export_xlsx(case, investigations) -> bytes:
    """Return XLSX bytes using openpyxl."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        raise RuntimeError("openpyxl not installed. Run: pip install openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"
    # Header styles
    title_font = Font(bold=True, size=14, color="4338CA")
    hdr_font = Font(bold=True, color="FFFFFF")
    hdr_fill = PatternFill("solid", fgColor="4338CA")
    # Title
    ws.append(["OSINT Investigation Report"])
    ws["A1"].font = title_font
    ws.append(["Case", case.title])
    ws.append(["Status", case.status.replace("_", " ").title()])
    ws.append(["Priority", case.priority.title()])
    ws.append(["Created", case.created_at.strftime('%Y-%m-%d %H:%M') if case.created_at else ""])
    if case.description:
        ws.append(["Description", case.description])
    ws.append(["Generated", datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M') + " UTC"])
    ws.append([])
    # Column headers
    hdrs = ["#", "Type", "Query", "Date", "Summary"]
    ws.append(hdrs)
    hdr_row = ws.max_row
    for col_i, _ in enumerate(hdrs, 1):
        cell = ws.cell(row=hdr_row, column=col_i)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center")
    # Data rows
    alt_fill = PatternFill("solid", fgColor="EEF2FF")
    for i, inv in enumerate(investigations, 1):
        summary = _format_result(inv.result_json).replace('\n', ' | ')[:500]
        ts = inv.created_at.strftime('%Y-%m-%d %H:%M') if inv.created_at else ""
        ws.append([i, inv.kind.replace("_", " ").title(), inv.query, ts, summary])
        if i % 2 == 0:
            for col_i in range(1, 6):
                ws.cell(row=ws.max_row, column=col_i).fill = alt_fill
    # Column widths
    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 30
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 70
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
