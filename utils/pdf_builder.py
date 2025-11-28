from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Circle, Wedge, String, Rect
from datetime import datetime
from io import BytesIO


# -----------------------------------------------------------
# ORIGINAL PAGE-BUILDING LOGIC (unchanged)
# -----------------------------------------------------------
def generate_pdf_story(
    url,
    main_score,
    content_score,
    technical_score,
    keyword_score,
    onpage_score,
    link_score,
    audit_text,
    tips_text,
    competitor_data=None
):
    styles = getSampleStyleSheet()
    story = []

    # Header Bar
    header = Drawing(500, 40)
    header.add(Rect(0, 0, 500, 40, fillColor=colors.HexColor("#6A4CFF")))
    header.add(String(15, 12, "SEO Booster Pro", fontSize=16, fillColor=colors.white))
    story.append(header)
    story.append(Spacer(1, 12))

    # URL + DATE
    meta_style = ParagraphStyle(
        name="meta",
        fontSize=11,
        textColor=colors.black,
        leading=14
    )
    story.append(Paragraph(f"<b>URL Scanned:</b> {url}", meta_style))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", meta_style))
    story.append(Spacer(1, 16))

    # Score Circle
    score_draw = Drawing(200, 140)
    score_draw.add(Circle(70, 70, 60, fillColor=colors.HexColor("#E0E0E0"), strokeColor=None))

    angle = int(360 * (main_score / 100))
    if angle > 0:
        score_draw.add(Wedge(70, 70, 60, 0, angle, fillColor=colors.HexColor("#6A4CFF"), strokeColor=None))

    score_draw.add(Circle(70, 70, 40, fillColor=colors.white, strokeColor=None))
    score_draw.add(String(57, 66, str(main_score), fontSize=26, fillColor=colors.HexColor("#333333")))
    score_draw.add(String(48, 40, "Score", fontSize=12, fillColor=colors.HexColor("#666666")))
    story.append(score_draw)
    story.append(Spacer(1, 20))

    # Subscores Table
    table_data = [
        ["Metric", "Score"],
        ["Content Quality", f"{content_score}%"],
        ["Keyword Relevance", f"{keyword_score}%"],
        ["Technical Health", f"{technical_score}%"],
        ["On-Page Structure", f"{onpage_score}%"],
        ["Link Health", f"{link_score}%"],
    ]

    t = Table(table_data, colWidths=[200, 100])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6A4CFF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.gray),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # Audit
    story.append(Paragraph("<b>Site Audit Summary</b>", styles["Heading3"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(audit_text.replace("\n", "<br/>"), styles["BodyText"]))
    story.append(Spacer(1, 16))

    # Tips
    story.append(Paragraph("<b>Optimization Tips</b>", styles["Heading3"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(tips_text.replace("\n", "<br/>"), styles["BodyText"]))
    story.append(Spacer(1, 16))

    # Competitor Table (optional)
    if competitor_data:
        story.append(Paragraph("<b>Competitor Comparison</b>", styles["Heading3"]))
        story.append(Spacer(1, 8))

        comp_table = Table([
            ["Metric", "You", "Competitor"],
            ["Content", f"{content_score}%", f"{competitor_data['content']}%"],
            ["Keyword", f"{keyword_score}%", f"{competitor_data['keyword']}%"],
            ["Technical", f"{technical_score}%", f"{competitor_data['technical']}%"],
            ["On-Page", f"{onpage_score}%", f"{competitor_data['onpage']}%"],
            ["Links", f"{link_score}%", f"{competitor_data['links']}%"],
        ], colWidths=[160, 90, 120])

        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6A4CFF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.gray),
        ]))

        story.append(comp_table)
        story.append(Spacer(1, 20))

    return story


# -----------------------------------------------------------
# PUBLIC API (CALLED BY app.py)
# -----------------------------------------------------------
def build_pdf(user_data, analysis_data, competitor_data=None):
    """
    Converts /scan JSON directly into a downloadable PDF (bytes).
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    story = generate_pdf_story(
        url=analysis_data.get("url", "N/A"),
        main_score=analysis_data["score"],
        content_score=analysis_data["content"],
        technical_score=analysis_data["technical"],
        keyword_score=analysis_data["keyword"],
        onpage_score=analysis_data["onpage"],
        link_score=analysis_data["links"],
        audit_text=analysis_data["audit"],
        tips_text=analysis_data["tips"],
        competitor_data=competitor_data
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
