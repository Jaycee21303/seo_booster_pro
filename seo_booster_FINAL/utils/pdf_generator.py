from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import uuid
import textwrap

def create_pdf_report(report_text):
    """
    Creates a professional PDF report for SEO Booster Pro.
    Returns the filename so it can be downloaded.
    """

    filename = f"seo_report_{uuid.uuid4()}.pdf"

    # Create PDF
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "SEO Booster Pro - Website Audit Report")

    # Separator line
    c.setLineWidth(1)
    c.line(50, height - 60, width - 50, height - 60)

    # Body text
    c.setFont("Helvetica", 12)

    y_position = height - 100
    line_height = 16

    # Wrap long lines
    wrapped_lines = textwrap.wrap(report_text, 100)

    for line in wrapped_lines:
        c.drawString(50, y_position, line)
        y_position -= line_height

        # If page is full, start new page
        if y_position < 50:
            c.showPage()
            c.setFont("Helvetica", 12)
            y_position = height - 50

    c.save()
    return filename
