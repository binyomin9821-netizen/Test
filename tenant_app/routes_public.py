"""
Public pages -- no login. The application form, its confirmation page,
and the applicant self-service status/inspection-booking page.
"""
from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import update

from tenant_app.extensions import db
from tenant_app.models import Application, InspectionSlot, Property

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    return redirect(url_for("public.apply"))


@public_bp.route("/apply", methods=["GET", "POST"])
def apply():
    properties = Property.query.order_by(Property.name).all()

    if request.method == "POST":
        errors = []
        property_id = request.form.get("property_id", "").strip()
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        current_address = request.form.get("current_address", "").strip()
        marital_status = request.form.get("marital_status", "").strip()
        number_of_children = request.form.get("number_of_children", "").strip()

        valid_property_ids = {str(p.id) for p in properties}
        if not property_id:
            errors.append("Please choose a property.")
        elif property_id not in valid_property_ids:
            errors.append("Please choose a valid property from the list.")
        if not full_name:
            errors.append("Please enter your full name.")
        if not phone:
            errors.append("Please enter your phone number.")
        if not email:
            errors.append("Please enter your email address.")
        if not current_address:
            errors.append("Please enter your current address.")

        children_value = None
        if number_of_children:
            try:
                children_value = int(number_of_children)
            except ValueError:
                errors.append("Number of children must be a whole number.")

        if errors:
            return render_template("apply.html", properties=properties, errors=errors, form=request.form)

        application = Application(
            property_id=int(property_id), full_name=full_name, phone=phone, email=email,
            current_address=current_address, marital_status=marital_status or None,
            number_of_children=children_value,
        )
        db.session.add(application)
        db.session.commit()
        return redirect(url_for("public.confirmation", application_id=application.id))

    return render_template("apply.html", properties=properties, errors=[], form={})


@public_bp.route("/confirmation/<int:application_id>")
def confirmation(application_id):
    application = Application.query.get(application_id)
    if application is None:
        return redirect(url_for("public.apply"))
    return render_template("confirmation.html", application=application)


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
                if my_slot is None and application.status != "Denied":
                    open_slots = (
                        InspectionSlot.query.filter_by(application_id=None)
                        .order_by(InspectionSlot.slot_time)
                        .all()
                    )

    return render_template(
        "status.html", application=application, error=error,
        booked_message=booked_message, my_slot=my_slot, open_slots=open_slots,
    )
