"""
The paper-application intake flow: staff (admin or property manager)
upload a photo/scan of a completed paper application, OCR takes a best
effort at reading it, and a human reviews and corrects every field
before anything is saved. OCR output is never saved on its own -- see
the review step below.

Available to both roles (pm_required allows admins too); the property
dropdown is scoped to whatever properties the current user can see.
"""
import os
import time
import uuid
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename

from tenant_app.auth import pm_required, visible_property_ids
from tenant_app.extensions import db
from tenant_app.models import Application, HouseholdMember, Property
from tenant_app.ocr import extract_text, guess_property_id

intake_bp = Blueprint("intake", __name__, url_prefix="/intake")

ALLOWED_SCAN_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "heic", "pdf"}
HOUSEHOLD_ROWS = 5


def allowed_scan(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_SCAN_EXTENSIONS


def _visible_properties():
    ids = visible_property_ids(current_user)
    query = Property.query
    if ids is not None:
        query = query.filter(Property.id.in_(ids or [-1]))
    return query.order_by(Property.name).all()


def _decimal_or_none(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _int_or_none(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _date_or_none(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


@intake_bp.route("/upload", methods=["GET", "POST"])
@pm_required
def upload():
    properties = _visible_properties()

    if request.method == "POST":
        scan = request.files.get("scan")
        if not scan or not scan.filename or not allowed_scan(scan.filename):
            flash("Please choose a photo or scan of the completed paper form (JPG, PNG, WEBP, HEIC, or PDF).")
            return render_template("intake_upload.html", properties=properties)

        tmp_dir = os.path.join(current_app.instance_path, "uploads", "_intake_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        safe_name = secure_filename(scan.filename)
        tmp_name = f"{uuid.uuid4().hex}_{safe_name}"
        tmp_path = os.path.join(tmp_dir, tmp_name)
        scan.save(tmp_path)

        raw_text = extract_text(tmp_path)
        guessed_property_id = guess_property_id(raw_text, properties)

        return render_template(
            "intake_review.html",
            properties=properties,
            raw_text=raw_text,
            temp_filename=tmp_name,
            image_url=url_for("uploaded_file", filename=f"_intake_tmp/{tmp_name}"),
            guessed_property_id=guessed_property_id,
            household_rows=range(HOUSEHOLD_ROWS),
            errors=[],
            form={},
        )

    return render_template("intake_upload.html", properties=properties)


@intake_bp.route("/create", methods=["POST"])
@pm_required
def create():
    properties = _visible_properties()
    valid_property_ids = {str(p.id) for p in properties}

    temp_filename = request.form.get("temp_filename", "")
    property_id = request.form.get("property_id", "").strip()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    current_address = request.form.get("current_address", "").strip()
    consent_given = request.form.get("consent_given") == "on"
    signature_name = request.form.get("signature_name", "").strip()

    errors = []
    if not property_id or property_id not in valid_property_ids:
        errors.append("Please choose a valid property.")
    if not full_name:
        errors.append("Please enter the applicant's full legal name.")
    if not phone:
        errors.append("Please enter a phone number.")
    if not email:
        errors.append("Please enter an email address.")
    if not current_address:
        errors.append("Please enter the applicant's current address.")
    if not consent_given:
        errors.append("The paper form must show the applicant's signature before this can be saved.")

    tmp_dir = os.path.join(current_app.instance_path, "uploads", "_intake_tmp")
    tmp_path = os.path.join(tmp_dir, temp_filename) if temp_filename else None
    if not temp_filename or not os.path.isfile(tmp_path):
        errors.append("The uploaded scan was lost -- please upload it again.")

    if errors:
        return render_template(
            "intake_review.html",
            properties=properties,
            raw_text=request.form.get("raw_text", ""),
            temp_filename=temp_filename,
            image_url=url_for("uploaded_file", filename=f"_intake_tmp/{temp_filename}") if temp_filename else None,
            guessed_property_id=None,
            household_rows=range(HOUSEHOLD_ROWS),
            errors=errors,
            form=request.form,
        )

    application = Application(
        property_id=int(property_id),
        full_name=full_name,
        date_of_birth=_date_or_none(request.form.get("date_of_birth")),
        phone=phone,
        email=email,
        current_address=current_address,
        marital_status=request.form.get("marital_status", "").strip() or None,
        number_of_children=_int_or_none(request.form.get("number_of_children")),
        employer_name=request.form.get("employer_name", "").strip() or None,
        employer_contact=request.form.get("employer_contact", "").strip() or None,
        income_employment=_decimal_or_none(request.form.get("income_employment")),
        income_benefits=_decimal_or_none(request.form.get("income_benefits")),
        income_other=_decimal_or_none(request.form.get("income_other")),
        signature_name=signature_name or None,
        consent_given=consent_given,
        ocr_extracted_text=request.form.get("raw_text", ""),
    )
    ssn = request.form.get("ssn", "").strip()
    if ssn:
        application.ssn = ssn

    status = "Waitlisted"
    property_ = Property.query.get(int(property_id))
    if property_ and property_.vacant_unit_count > 0:
        status = "Active — unit available"
    application.status = status

    db.session.add(application)
    db.session.flush()  # assigns application.id

    for i in range(HOUSEHOLD_ROWS):
        name = request.form.get(f"household_name_{i}", "").strip()
        if not name:
            continue
        db.session.add(HouseholdMember(
            application_id=application.id,
            name=name,
            date_of_birth=_date_or_none(request.form.get(f"household_dob_{i}")),
            relationship_to_applicant=request.form.get(f"household_relationship_{i}", "").strip() or None,
        ))

    final_dir = os.path.join(current_app.instance_path, "uploads", str(application.id))
    os.makedirs(final_dir, exist_ok=True)
    final_name = f"paper_form_{int(time.time())}{os.path.splitext(temp_filename)[1]}"
    os.replace(tmp_path, os.path.join(final_dir, final_name))
    application.paper_form_photo_path = f"{application.id}/{final_name}"

    db.session.commit()

    flash(f"Application #{application.id} saved with status: {status}.")
    if current_user.is_admin:
        return redirect(url_for("admin.application_detail", application_id=application.id))
    return redirect(url_for("pm.application_detail", application_id=application.id))
