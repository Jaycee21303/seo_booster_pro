from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
import html


def safe(value, default="N/A"):
    """Convert any type to a safe printable string."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return ", ".join([safe(v) for v in value])
    value = str(value).strip()
    if value == "":
        return default
    return html.escape(value)  # escape all unsafe chars for PDF/XML


def section(title):
    return Paragraph(f"<b><font size=14 color='#6A4CFF'>{html.escape(title)}</font></b>")


def build_pdf(user_data, analysis_data, competitor_data=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    # -----------------------
    # PDF Story Container
    # -----------------------
    story = []

    # =========================
    # HEADER
    # =========================
    story.append(Paragraph("<b><font size=18>SEO Booster Pro Report</font></b>", styles["Title"]))
    story.append(Spacer(1, 0.25 * inch))

    # =========================
    # USER INFO
    # =========================
    story.append(section("User"))
    story.append(Paragraph(f"Email: {safe(user_data.get('email'))}", normal))
    story.append(Spacer(1, 0.25 * inch))

    # =========================
    # ANALYSIS SUMMARY
    # =========================
    story.append(section("Analysis Overview"))

    story.append(Paragraph(f"Main Score: {safe(analysis_data.get('score'))}", normal))
    story.append(Paragraph(f"Content Quality: {safe(analysis_data.get('content'))}", normal))
    story.append(Paragraph(f"Keyword Relevance: {safe(analysis_data.get('keyword'))}", normal))
    story.append(Paragraph(f"Technical Health: {safe(analysis_data.get('technical'))}", normal))
    story.append(Paragraph(f"On-Page Structure: {safe(analysis_data.get('onpage'))}", normal))
    story.append(Paragraph(f"Link Health: {safe(analysis_data.get('links'))}", normal))

    story.append(Spacer(1, 0.25 * inch))

    # =========================
    # AUDIT SECTION
    # =========================
    story.append(section("Site Audit"))

    audit_text = safe(analysis_data.get("audit"))
    for line in audit_text.split("\n"):
        line = line.strip()
        if line:
            story.append(Paragraph(f"- {html.escape(line)}", normal))

    story.append(Spacer(1, 0.25 * inch))

    # =========================
    # TIPS SECTION
    # =========================
    story.append(section("Optimization Tips"))

    tips_text = safe(analysis_data.get("tips"))
    for tip in tips_text.split("\n"):
        tip = tip.strip()
        if tip:
            story.append(Paragraph(f"• {html.escape(tip)}", normal))

    story.append(Spacer(1, 0.25 * inch))

    # =========================
    # COMPETITOR SECTION
    # =========================
    if competitor_data:
        story.append(section("Competitor Comparison"))

        story.append(Paragraph(f"Competitor Score: {safe(competitor_data.get('score'))}", normal))
        story.append(Paragraph(f"Content: {safe(competitor_data.get('content'))}", normal))
        story.append(Paragraph(f"Keyword: {safe(competitor_data.get('keyword'))}", normal))
        story.append(Paragraph(f"Technical: {safe(competitor_data.get('technical'))}", normal))
        story.append(Paragraph(f"On-Page: {safe(competitor_data.get('onpage'))}", normal))
        story.append(Paragraph(f"Links: {safe(competitor_data.get('links'))}", normal))

        story.append(Spacer(1, 0.25 * inch))

    # =========================
    # BUILD FINAL PDF
    # =========================
    doc.build(story)

    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

