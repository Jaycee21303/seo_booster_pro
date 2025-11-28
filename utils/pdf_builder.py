from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO


def safe(value, default="N/A"):
    """Safely return text without crashing the PDF."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return str(value)
    if not isinstance(value, str):
        return default
    if value.strip() == "":
        return default
    return value


def section(title):
    """Styled section title."""
    return Paragraph(f"<b><font size=14 color='#6A4CFF'>{title}</font></b>")


def build_pdf(user_data, analysis_data, competitor_data=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
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
    story.append(Paragraph(f"Email: {safe(user_data.get('email'))}", styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))

    # =========================
    # ANALYSIS SUMMARY
    # =========================
    story.append(section("Analysis Overview"))

    story.append(Paragraph(f"Main Score: {safe(analysis_data.get('score'))}", styles["Normal"]))

    story.append(Paragraph(f"Content Quality: {safe(analysis_data.get('content'))}", styles["Normal"]))
    story.append(Paragraph(f"Keyword Relevance: {safe(analysis_data.get('keyword'))}", styles["Normal"]))
    story.append(Paragraph(f"Technical Health: {safe(analysis_data.get('technical'))}", styles["Normal"]))
    story.append(Paragraph(f"On-Page Structure: {safe(analysis_data.get('onpage'))}", styles["Normal"]))
    story.append(Paragraph(f"Link Health: {safe(analysis_data.get('links'))}", styles["Normal"]))

    story.append(Spacer(1, 0.25 * inch))

    # =========================
    # AUDIT SECTION
    # =========================
    story.append(section("Site Audit"))
    audit_text = safe(analysis_data.get("audit"))
    audit_lines = audit_text.split("\n")
    for line in audit_lines:
        story.append(Paragraph(f"- {line}", styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))

    # =========================
    # TIPS SECTION
    # =========================
    story.append(section("Optimization Tips"))
    tips_text = safe(analysis_data.get("tips"))
    tips_lines = tips_text.split("\n")
    for tip in tips_lines:
        story.append(Paragraph(f"• {tip}", styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))

    # =========================
    # COMPETITOR SECTION (PRO)
    # =========================
    if competitor_data:
        story.append(section("Competitor Comparison"))
        story.append(Paragraph(f"Competitor Score: {safe(competitor_data.get('score'))}", styles["Normal"]))

        story.append(Paragraph(f"Content: {safe(competitor_data.get('content'))}", styles["Normal"]))
        story.append(Paragraph(f"Keyword: {safe(competitor_data.get('keyword'))}", styles["Normal"]))
        story.append(Paragraph(f"Technical: {safe(competitor_data.get('technical'))}", styles["Normal"]))
        story.append(Paragraph(f"On-Page: {safe(competitor_data.get('onpage'))}", styles["Normal"]))
        story.append(Paragraph(f"Links: {safe(competitor_data.get('links'))}", styles["Normal"]))

        story.append(Spacer(1, 0.25 * inch))

    # =========================
    # BUILD PDF
    # =========================
    doc.build(story)

    pdf_data = buffer.getvalue()
    buffer.close()

    return pdf_data
