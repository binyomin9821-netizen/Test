"""
Admin-only pages: the full applications dashboard, property management,
property-manager account management, and inspection-slot management.
Everything here sees the whole portfolio -- no property filtering.
"""
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from tenant_app import mail
from tenant_app.auth import admin_required
from tenant_app.extensions import db
from tenant_app.models import (
    Application, InspectionPhoto, InspectionSlot, Property, PropertyAssignment, User,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def dashboard():
    applications = (
        Application.query.join(Property)
        .order_by(Application.created_at.desc(), Application.id.desc())
        .all()
    )
    return render_template("dashboard.html", applications=applications)


@admin_bp.route("/properties", methods=["GET", "POST"])
@admin_required
def properties():
    errors = []

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        manager_email = request.form.get("manager_email", "").strip()
        manager_phone = request.form.get("manager_phone", "").strip()

        if not name:
            errors.append("Please enter a property name.")
        if not address:
            errors.append("Please enter an address.")

        if not errors:
            db.session.add(Property(
                name=name, address=address,
                manager_email=manager_email or None,
                manager_phone=manager_phone or None,
            ))
            db.session.commit()
            return redirect(url_for("admin.properties"))

    all_properties = Property.query.order_by(Property.name).all()
    pending_counts = dict(
        db.session.query(Application.property_id, db.func.count(Application.id))
        .filter(Application.status == "Pending")
        .group_by(Application.property_id)
        .all()
    )
    total_counts = dict(
        db.session.query(Application.property_id, db.func.count(Application.id))
        .group_by(Application.property_id)
        .all()
    )

    return render_template(
        "admin_properties.html",
        properties=all_properties,
        pending_counts=pending_counts,
        total_counts=total_counts,
        errors=errors,
        form=request.form,
    )


@admin_bp.route("/property-managers", methods=["GET", "POST"])
@admin_required
def property_managers():
    errors = []
    all_properties = Property.query.order_by(Property.name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        property_ids = [int(pid) for pid in request.form.getlist("property_ids")]

        if not name:
            errors.append("Please enter a name.")
        if not email:
            errors.append("Please enter an email.")
        elif User.query.filter_by(email=email).first():
            errors.append("That email is already in use.")
        if not password or len(password) < 8:
            errors.append("Please set a password of at least 8 characters.")
        if not property_ids:
            errors.append("Please assign at least one property.")

        if not errors:
            user = User(name=name, email=email, role="property_manager")
            user.set_password(password)
            db.session.add(user)
            db.session.flush()  # assigns user.id before we reference it below
            for property_id in property_ids:
                db.session.add(PropertyAssignment(user_id=user.id, property_id=property_id))
            db.session.commit()
            return redirect(url_for("admin.property_managers"))

    managers = User.query.filter_by(role="property_manager").order_by(User.name).all()
    return render_template(
        "admin_property_managers.html",
        managers=managers,
        properties=all_properties,
        errors=errors,
        form=request.form,
    )


@admin_bp.route("/inspections", methods=["GET", "POST"])
@admin_required
def inspections():
    if request.method == "POST":
        slot_time = request.form.get("slot_time", "").strip()
        if slot_time:
            db.session.add(InspectionSlot(slot_time=slot_time))
            db.session.commit()
        return redirect(url_for("admin.inspections"))

    slots = InspectionSlot.query.order_by(InspectionSlot.slot_time).all()
    return render_template("admin_inspections.html", slots=slots)


@admin_bp.route("/application/<int:application_id>")
@admin_required
def application_detail(application_id):
    application = Application.query.get_or_404(application_id)
    photos = (
        InspectionPhoto.query.filter_by(application_id=application_id)
        .order_by(InspectionPhoto.uploaded_at.desc())
        .all()
    )
    return render_template("detail.html", application=application, photos=photos)


@admin_bp.route("/application/<int:application_id>/decide", methods=["POST"])
@admin_required
def decide(application_id):
    application = Application.query.get_or_404(application_id)
    new_status = request.form.get("decision")
    if new_status not in ("Approved", "Denied"):
        return redirect(url_for("admin.application_detail", application_id=application_id))

    application.status = new_status
    application.decision_date = date.today()
    db.session.commit()

    sent, error = mail.send_decision_email(
        application.email, application.full_name, application.property.name,
        new_status, application.id,
    )
    if sent:
        flash(f"Application {new_status.lower()}. Email sent to {application.email}.")
    else:
        flash(f"Application {new_status.lower()}. Email was not sent: {error}")

    return redirect(url_for("admin.application_detail", application_id=application_id))
