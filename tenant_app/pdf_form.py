"""
Generates the printable paper application as a PDF, with boxed
character grids (one box per letter/digit, where practical) to help OCR
accuracy on the handwritten scans that come back in through the intake
flow (see routes_intake.py / ocr.py).

Deliberately has no disability/accommodation field -- that was scoped
for this phase but held back pending legal review of exact wording, per
an explicit decision made when this was built. Don't add one here
without checking first.
"""
import io

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

BOX = 0.19 * inch
GAP = 0.02 * inch
MARGIN = 0.75 * inch
PAGE_W, PAGE_H = letter
# Available width is PAGE_W - 2*MARGIN = 504pt; at BOX+GAP pitch (~15.1pt)
# that's room for ~33 boxes. Every box-grid field below stays at 30 or
# fewer to leave a safety margin.


def _boxes(c, x, y, count, box=BOX, gap=GAP):
    """Draws `count` empty character boxes starting at (x, y), left to
    right. Returns the x position just past the last box."""
    for i in range(count):
        bx = x + i * (box + gap)
        c.rect(bx, y, box, box)
    return x + count * (box + gap)


def _label(c, x, y, text, size=9):
    c.setFont("Helvetica", size)
    c.drawString(x, y, text)


def _section(c, x, y, text):
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, text)
    c.line(x, y - 4, PAGE_W - MARGIN, y - 4)


def _field_with_boxes(c, x, y, label, count, box=BOX):
    """A label above a row of boxes. Returns the y for the next field
    below this one."""
    _label(c, x, y, label)
    _boxes(c, x, y - box - 2, count, box=box)
    return y - box - 22


def generate_application_pdf():
    """Returns a BytesIO containing the finished PDF, ready to send with
    Flask's send_file."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    x = MARGIN
    y = PAGE_H - MARGIN

    # ---- Page 1 ----
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, "Affordable Housing Application")
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(x, y, "Please print clearly, one letter or number per box. Use black or blue ink.")
    y -= 26

    _section(c, x, y, "Property")
    y -= 24
    _label(c, x, y, "Which property are you applying to? (write the full property name)")
    y -= BOX + 2
    _boxes(c, x, y, 30)
    y -= 30

    _section(c, x, y, "Applicant Information")
    y -= 24
    y = _field_with_boxes(c, x, y, "Full Legal Name", 30)

    _label(c, x, y, "Date of Birth (MM / DD / YYYY)")
    y -= BOX + 2
    end_x = _boxes(c, x, y, 2)
    _label(c, end_x + 4, y + BOX / 2 - 3, "/")
    end_x = _boxes(c, end_x + 14, y, 2)
    _label(c, end_x + 4, y + BOX / 2 - 3, "/")
    _boxes(c, end_x + 14, y, 4)
    y -= 22

    _label(c, x, y, "Social Security Number (XXX - XX - XXXX)")
    y -= BOX + 2
    end_x = _boxes(c, x, y, 3)
    _label(c, end_x + 4, y + BOX / 2 - 3, "-")
    end_x = _boxes(c, end_x + 14, y, 2)
    _label(c, end_x + 4, y + BOX / 2 - 3, "-")
    _boxes(c, end_x + 14, y, 4)
    y -= 22

    y = _field_with_boxes(c, x, y, "Phone Number", 14)
    y = _field_with_boxes(c, x, y, "Email Address", 30)
    y = _field_with_boxes(c, x, y, "Current Street Address", 30)
    y = _field_with_boxes(c, x, y, "Current City / State / ZIP", 30)

    _label(c, x, y, "Marital Status (check one)")
    y -= 16
    for i, option in enumerate(["Single", "Married", "Divorced", "Widowed"]):
        ox = x + i * 1.6 * inch
        c.rect(ox, y, 12, 12)
        _label(c, ox + 18, y + 1, option)
    y -= 28

    y = _field_with_boxes(c, x, y, "Number of Dependents", 2)

    c.showPage()

    # ---- Page 2 ----
    x = MARGIN
    y = PAGE_H - MARGIN

    _section(c, x, y, "Household Members (other than yourself)")
    y -= 24
    col_name, col_dob, col_rel = x, x + 3.2 * inch, x + 5.0 * inch
    _label(c, col_name, y, "Name", 9)
    _label(c, col_dob, y, "Date of Birth", 9)
    _label(c, col_rel, y, "Relationship to Applicant", 9)
    y -= 6
    for _ in range(5):
        y -= 26
        c.line(col_name, y, col_dob - 10, y)
        c.line(col_dob, y, col_rel - 10, y)
        c.line(col_rel, y, PAGE_W - MARGIN, y)
    y -= 30

    _section(c, x, y, "Employment")
    y -= 24
    y = _field_with_boxes(c, x, y, "Employer Name", 30)
    y = _field_with_boxes(c, x, y, "Employer Phone Number", 14)

    _section(c, x, y, "Monthly Household Income")
    y -= 24
    _label(c, x, y, "Employment income ($)")
    y -= BOX + 2
    _boxes(c, x, y, 6)
    y -= 22
    _label(c, x, y, "Benefits income ($) (SSI, SSDI, TANF, etc.)")
    y -= BOX + 2
    _boxes(c, x, y, 6)
    y -= 22
    _label(c, x, y, "Other income ($)")
    y -= BOX + 2
    _boxes(c, x, y, 6)
    y -= 34

    _section(c, x, y, "Consent")
    y -= 20
    c.setFont("Helvetica", 9)
    text = c.beginText(x, y)
    text.setLeading(13)
    for line in [
        "By signing below, I certify that the information on this application is true and complete to",
        "the best of my knowledge. I understand that this information will be used to determine my",
        "eligibility for housing, and that providing false information may result in denial of my",
        "application.",
    ]:
        text.textLine(line)
    c.drawText(text)
    y -= 60

    c.line(x, y, x + 3 * inch, y)
    _label(c, x, y - 12, "Applicant Signature")
    c.line(x + 3.4 * inch, y, x + 5.4 * inch, y)
    _label(c, x + 3.4 * inch, y - 12, "Printed Name")

    y -= 40
    _label(c, x, y, "Date signed (MM / DD / YYYY)")
    y -= BOX + 2
    end_x = _boxes(c, x, y, 2)
    end_x = _boxes(c, end_x + 14, y, 2)
    _boxes(c, end_x + 14, y, 4)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
