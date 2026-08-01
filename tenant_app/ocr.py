"""
Reads text off a scanned/photographed paper application using Tesseract
(free, runs locally, no account or API key needed).

Handwriting accuracy from Tesseract is genuinely limited -- it's built
for printed text, not handwriting. Expect this to give a rough, messy
transcription at best. That's why nothing here tries to be clever about
parsing structured fields out of it (dates, SSNs, income) -- it just
surfaces the raw text and a best-effort guess at which property the form
is for, and leaves every field for a human to fill in or correct on the
review screen. See README.md for the tradeoff against a paid OCR API,
which would do meaningfully better on handwriting if this isn't accurate
enough in practice.
"""
import difflib

import pytesseract
from PIL import Image


def extract_text(image_path):
    try:
        image = Image.open(image_path)
        return pytesseract.image_to_string(image)
    except Exception as exc:
        return f"[OCR failed: {exc}]"


def guess_property_id(raw_text, properties):
    """Best-effort match of the property name against the OCR'd text.
    Returns a property id, or None if nothing looked like a plausible
    match. This is a starting guess for the review screen, never used to
    save an application without a human confirming it."""
    text_lower = raw_text.lower()
    best_id, best_ratio = None, 0.0

    for property_ in properties:
        name_lower = property_.name.lower()
        if name_lower in text_lower:
            return property_.id  # exact substring match, easy case
        ratio = difflib.SequenceMatcher(None, name_lower, text_lower).ratio()
        if ratio > best_ratio:
            best_id, best_ratio = property_.id, ratio

    return best_id if best_ratio > 0.3 else None
