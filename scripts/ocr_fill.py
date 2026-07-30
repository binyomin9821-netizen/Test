"""Extract Name / Email / Marital Status from a scanned paper application and
stage them onto an existing `applications` row for human review.

Handwriting OCR is unreliable, and this data feeds a database that a person
uses to make a housing decision, so this script deliberately does NOT
silently overwrite existing values or bypass review:
  - it only fills fields that are currently blank
  - it always sets ocr_needs_review = True and stores the raw OCR text
  - by default it prints the proposed changes and asks for confirmation;
    pass --yes to apply without prompting (e.g. for a batch job that still
    lands in the review queue)

Usage:
    python scripts/ocr_fill.py --application-id 42 --image scan.jpg
    python scripts/ocr_fill.py --application-id 42 --image scan.jpg --engine gcv
    python scripts/ocr_fill.py --application-id 42 --image scan.jpg --yes
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tenant_app import create_app, db
from tenant_app.models import Application
from tenant_app.routes_public import MARITAL_STATUS_OPTIONS

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
LABELED_LINE_RE = re.compile(r"^\s*(?P<label>[A-Za-z ]{2,30})\s*[:\-]\s*(?P<value>.+)$")


def extract_text_tesseract(image_path):
    import pytesseract
    from PIL import Image

    return pytesseract.image_to_string(Image.open(image_path))


def extract_text_google_vision(image_path):
    from google.cloud import vision

    client = vision.ImageAnnotatorClient()
    with open(image_path, "rb") as f:
        content = f.read()
    image = vision.Image(content=content)
    # DOCUMENT_TEXT_DETECTION handles dense/handwritten text better than
    # plain TEXT_DETECTION.
    response = client.document_text_detection(image=image)
    if response.error.message:
        raise RuntimeError(response.error.message)
    return response.full_text_annotation.text


def parse_fields(raw_text):
    """Best-effort extraction. Returns a dict with any of name/email/marital_status found."""
    fields = {}

    email_match = EMAIL_RE.search(raw_text)
    if email_match:
        fields["email"] = email_match.group(0)

    for line in raw_text.splitlines():
        match = LABELED_LINE_RE.match(line)
        if not match:
            continue
        label = match.group("label").strip().lower()
        value = match.group("value").strip()

        if "name" in label and "email" not in label and "full_name" not in fields:
            fields["full_name"] = value
        elif "marital" in label:
            for option in MARITAL_STATUS_OPTIONS:
                if option.lower() in value.lower():
                    fields["marital_status"] = option
                    break

    return fields


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--application-id", type=int, required=True)
    parser.add_argument("--image", required=True, help="Path to the scanned application image")
    parser.add_argument("--engine", choices=["tesseract", "gcv"], default="tesseract")
    parser.add_argument("--yes", action="store_true", help="Apply without an interactive confirmation prompt")
    args = parser.parse_args()

    raw_text = extract_text_google_vision(args.image) if args.engine == "gcv" else extract_text_tesseract(args.image)
    if not raw_text.strip():
        print("No text could be extracted from the image.", file=sys.stderr)
        sys.exit(1)

    extracted = parse_fields(raw_text)
    if not extracted:
        print("Could not confidently extract any of Name / Email / Marital Status.", file=sys.stderr)
        print("--- Raw OCR text ---")
        print(raw_text)
        sys.exit(1)

    app = create_app()
    with app.app_context():
        application = Application.query.get(args.application_id)
        if not application:
            print(f"No application with id {args.application_id}.", file=sys.stderr)
            sys.exit(1)

        changes = {}
        for field in ("full_name", "email", "marital_status"):
            current_value = getattr(application, field)
            new_value = extracted.get(field)
            if new_value and not current_value:
                changes[field] = new_value

        if not changes:
            print(f"Application #{application.id} already has values for all extracted fields; nothing to fill.")
            print("Existing fields are never overwritten automatically — edit them manually if needed.")
            sys.exit(0)

        print(f"Proposed changes for application #{application.id} (engine={args.engine}):")
        for field, value in changes.items():
            print(f"  {field}: {value!r}")

        if not args.yes:
            confirm = input("Apply these changes? [y/N] ").strip().lower()
            if confirm != "y":
                print("Aborted, no changes made.")
                sys.exit(0)

        for field, value in changes.items():
            setattr(application, field, value)
        application.ocr_raw_text = raw_text
        application.ocr_needs_review = True
        db.session.commit()

        print(f"Applied. Application #{application.id} flagged ocr_needs_review=True for staff verification.")


if __name__ == "__main__":
    main()
