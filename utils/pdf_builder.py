from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Circle, Wedge, String, Rect
from reportlab.graphics import renderPDF
from datetime import datetime


# -----------------------------------------------------------
# CREATE PDF REPORT (ONE PAGE – POLISHED)
# -----------------------------------------------------------
def generate_pdf_report(
    filepath,
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
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    story = []

    # -------------------------------------------------------
    # HEADER BAR
    # -------------------------------------------------------
    header = Drawing(500, 40)
    header.add(Rect(0, 0, 500, 40, fillColor=colors.HexColor("#6A4CFF")))
    header.add(String(15, 12, "SEO Booster Pro", fontSize=16, fillColor=colors.white))
    story.append(header)
    story.append(Spacer(1, 12))

    # -------------------------------------------------------
    # URL + DATE
    # -------------------------------------------------------
    meta_style = ParagraphStyle(
        name="meta",
        fontSize=11,
        textColor=colors.black,
        leading=14
    )
    story.append(Paragraph(f"<b>URL Scanned:</b> {url}", meta_style))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", meta_style))
    story.append(Spacer(1, 16))

    # -------------------------------------------------------
    # SCORE CIRCLE (SC2 – Filled Arc)
    # -------------------------------------------------------
    score_draw = Drawing(200, 140)

    # Base circle background
    score_draw.add(Circle(70, 70, 60, fillColor=colors.HexColor("#E0E0E0"), strokeColor=None))

    # Purple arc (filled wedge)
    angle = int(360 * (main_score / 100))
    if angle > 0:
        score_draw.add(Wedge(70, 70, 60, 0, angle, fillColor=colors.HexColor("#6A4CFF"), strokeColor=None))

    # White center circle
    score_draw.add(Circle(70, 70, 40, fillColor=colors.white, strokeColor=None))

    # Score text
    score_draw.add(String(57, 66, str(main_score), fontSize=26, fillColor=colors.HexColor("#333333")))
    score_draw.add(String(48, 40, "Score", fontSize=12, fillColor=colors.HexColor("#666666")))

    story.append(score_draw)
    story.append(Spacer(1, 20))

    # -------------------------------------------------------
    # SUB-SCORES TABLE (one-page condensed)
    # -------------------------------------------------------
    table_data = [
        ["Metric", "Score"],
        ["Content Quality", f"{content_score}%"],
        ["Keyword Relevance", f"{keyword_score}%"],
        ["Technical Health", f"{technical_score}%"],
        ["On-Page Structure", f"{onpage_score}%"],
        ["Link Health", f"{link_score}%"]
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

    # -------------------------------------------------------
    # AUDIT SECTION
    # -------------------------------------------------------
    audit_title = Paragraph("<b>Site Audit Summary</b>", styles["Heading3"])
    story.append(audit_title)
    story.append(Spacer(1, 6))

    audit_box = Paragraph(audit_text.replace("\n", "<br/>"), styles["BodyText"])
    story.append(audit_box)
    story.append(Spacer(1, 16))

    # -------------------------------------------------------
    # OPTIMIZATION TIPS
    # -------------------------------------------------------
    tips_title = Paragraph("<b>Optimization Tips</b>", styles["Heading3"])
    story.append(tips_title)
    story.append(Spacer(1, 6))

    tips_box = Paragraph(tips_text.replace("\n", "<br/>"), styles["BodyText"])
    story.append(tips_box)
    story.append(Spacer(1, 16))

    # -------------------------------------------------------
    # COMPETITOR COMPARISON (Optional)
    # -------------------------------------------------------
    if competitor_data:
        comp_title = Paragraph("<b>Competitor Comparison</b>", styles["Heading3"])
        story.append(comp_title)
        story.append(Spacer(1, 8))

        comp_table = Table([
            ["Metric", "You", "Competitor"],
            ["Content", f"{content_score}%", f"{competitor_data['content_score']}%"],
            ["Keyword", f"{keyword_score}%", f"{competitor_data['keyword_score']}%"],
            ["Technical", f"{technical_score}%", f"{competitor_data['technical_score']}%"],
            ["On-Page", f"{onpage_score}%", f"{competitor_data['onpage_score']}%"],
            ["Links", f"{link_score}%", f"{competitor_data['link_score']}%"],
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

    # -------------------------------------------------------
    # BUILD PDF
    # -------------------------------------------------------
    doc.build(story)
