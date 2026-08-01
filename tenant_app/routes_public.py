"""
Public pages -- no login. An informational page explaining how to apply
(the printable PDF, per Phase 2 -- applications are paper-first now, no
more direct online self-entry), and the applicant self-service
status/inspection-booking page.
"""
from flask import Blueprint, redirect, render_template, request, send_file, url_for
from sqlalchemy import update

from tenant_app.extensions import db
from tenant_app.models import Application, InspectionSlot, Property
from tenant_app.pdf_form import generate_application_pdf

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    return redirect(url_for("public.apply"))


@public_bp.route("/apply")
def apply():
    properties = Property.query.order_by(Property.name).all()
    return render_template("apply.html", properties=properties)


@public_bp.route("/apply/form.pdf")
def application_pdf():
    return send_file(
        generate_application_pdf(), mimetype="application/pdf",
        as_attachment=False, download_name="affordable-housing-application.pdf",
    )


def _find_application(reference, email):
    return Application.query.filter(
        Application.id == reference, db.func.lower(Application.email) == email.lower(),
    ).first()


@public_bp.route("/status", methods=["GET", "POST"])
def check_status():
    application = None
    error = None
    booked_message = None
    my_slot = None
    open_slots = []

    if request.method == "POST":
        reference = request.form.get("reference", "").strip()
        email = request.form.get("email", "").strip()
        slot_id = request.form.get("slot_id", "").strip()

        if not reference or not email:
            error = "Please enter both your reference number and email."
        elif not reference.isdigit():
            error = "The reference number should be numbers only (for example, 3)."
        else:
            application = _find_application(reference, email)
            if application is None:
                error = "We couldn't find an application with that reference number and email."
            else:
                if slot_id:
                    # A plain "read the slot, then write it" would let two
                    # applicants both grab the same open slot if they
                    # submit at the same instant. This UPDATE ... WHERE
                    # is atomic at the database level: only one concurrent
                    # request can ever win it.
                    result = db.session.execute(
                        update(InspectionSlot)
                        .where(InspectionSlot.id == slot_id, InspectionSlot.application_id.is_(None))
                        .values(application_id=application.id)
                    )
                    if result.rowcount:
                        application.inspection_status = "Scheduled"
                        db.session.commit()
                        booked_message = "Your inspection time is booked!"
                    else:
                        db.session.rollback()
                        error = "Sorry, that time slot was just taken. Please pick another."

                my_slot = InspectionSlot.query.filter_by(application_id=application.id).first()
                if my_slot is None and application.status not in ("Denied", "Approved"):
                    open_slots = (
                        InspectionSlot.query.filter_by(application_id=None)
                        .order_by(InspectionSlot.slot_time)
                        .all()
                    )

    return render_template(
        "status.html", application=application, error=error,
        booked_message=booked_message, my_slot=my_slot, open_slots=open_slots,
    )
