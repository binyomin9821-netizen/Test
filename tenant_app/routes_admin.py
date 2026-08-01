"""
Admin-only pages: the full applications dashboard, property management
(including per-property vacancy/waitlist/inspection views),
property-manager account management, and inspection-slot management.
Everything here sees the whole portfolio -- no property filtering.
"""
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from tenant_app import mail, sla
from tenant_app.auth import admin_required
from tenant_app.crypto import mask_ssn
from tenant_app.extensions import db
from tenant_app.models import (
    Application, InspectionPhoto, InspectionSlot, Property, PropertyAssignment, Unit, User,
    WaitlistOverride,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def dashboard():
    sla.run_sla_check()
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

    search = request.args.get("q", "").strip()
    query = Property.query
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(Property.name.ilike(like), Property.address.ilike(like)))
    all_properties = query.order_by(Property.name).all()

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
        search=search,
    )


def _waitlist_query(property_id):
    return (
        Application.query.filter_by(property_id=property_id, status="Waitlisted")
        .order_by(Application.waitlist_prioritized.desc(), Application.created_at.asc())
    )


@admin_bp.route("/properties/<int:property_id>")
@admin_required
def property_detail(property_id):
    property_ = Property.query.get_or_404(property_id)
    applications = (
        Application.query.filter_by(property_id=property_id)
        .order_by(Application.created_at.desc())
        .all()
    )
    waitlist = _waitlist_query(property_id).all()
    active_inspections = [
        a for a in applications
        if a.status == "Approved for inspection" and a.inspection_status != "Completed"
    ]
    return render_template(
        "admin_property_detail.html",
        property=property_, applications=applications, waitlist=waitlist,
        active_inspections=active_inspections,
    )


@admin_bp.route("/properties/<int:property_id>/units/add", methods=["POST"])
@admin_required
def add_unit(property_id):
    Property.query.get_or_404(property_id)
    unit_number = request.form.get("unit_number", "").strip()
    if unit_number:
        db.session.add(Unit(property_id=property_id, unit_number=unit_number, status="vacant"))
        db.session.commit()
    return redirect(url_for("admin.property_detail", property_id=property_id))


@admin_bp.route("/properties/<int:property_id>/units/<int:unit_id>/toggle", methods=["POST"])
@admin_required
def toggle_unit(property_id, unit_id):
    unit = Unit.query.filter_by(id=unit_id, property_id=property_id).first_or_404()
    unit.status = "occupied" if unit.status == "vacant" else "vacant"
    db.session.commit()
    return redirect(url_for("admin.property_detail", property_id=property_id))


@admin_bp.route("/properties/<int:property_id>/waitlist/<int:application_id>/advance", methods=["POST"])
@admin_required
def advance_waitlist(property_id, application_id):

    application = Application.query.filter_by(id=application_id, property_id=property_id).first_or_404()
    reason = request.form.get("reason", "").strip()

    if application.status != "Waitlisted":
        flash("That application isn't on the waitlist.")
        return redirect(url_for("admin.property_detail", property_id=property_id))

    if not reason:
        flash("Please note a reason before moving someone off the waitlist -- this gets logged for compliance.")
        return redirect(url_for("admin.property_detail", property_id=property_id))

    db.session.add(WaitlistOverride(
        application_id=application.id, performed_by_id=current_user.id, reason=reason,
    ))
    application.status = "Active — unit available"
    db.session.commit()
    flash(f"Application #{application.id} moved to Active — unit available.")
    return redirect(url_for("admin.property_detail", property_id=property_id))


@admin_bp.route("/properties/<int:property_id>/waitlist/<int:application_id>/prioritize", methods=["POST"])
@admin_required
def prioritize_waitlist(property_id, application_id):

    application = Application.query.filter_by(id=application_id, property_id=property_id).first_or_404()
    reason = request.form.get("reason", "").strip()

    if not reason:
        flash("A reason is required to move someone ahead on the waitlist.")
        return redirect(url_for("admin.property_detail", property_id=property_id))

    application.waitlist_prioritized = True
    db.session.add(WaitlistOverride(
        application_id=application.id, performed_by_id=current_user.id, reason=reason,
    ))
    db.session.commit()
    flash(f"Application #{application.id} prioritized on the waitlist.")
    return redirect(url_for("admin.property_detail", property_id=property_id))


@admin_bp.route("/property-managers", methods=["GET", "POST"])
@admin_required
def property_managers():
    errors = []
    all_properties = Property.query.order_by(Property.name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        supervisor_email = request.form.get("supervisor_email", "").strip()
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
            user = User(
                name=name, email=email, role="property_manager",
                supervisor_email=supervisor_email or None,
            )
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


@admin_bp.route("/inspections/run-sla-check", methods=["POST"])
@admin_required
def run_sla_check_now():
    result = sla.run_sla_check(force=True)
    flash(
        f"SLA check ran: {result['checked']} pending inspection(s), "
        f"{result['reminders_sent']} reminder(s) sent, {result['escalations_sent']} escalation(s) sent."
    )
    return redirect(url_for("admin.inspections"))


@admin_bp.route("/testing-tools", methods=["GET", "POST"])
@admin_required
def testing_tools():
    """Dev/testing only: lets you fast-forward an application's inspection
    clock so you can see the 5-day SLA escalation without waiting 5 real
    days. See README.md "Testing the inspection SLA" for how to use this."""
    if request.method == "POST":
        application_id = request.form.get("application_id", "").strip()
        days_ago = request.form.get("days_ago", "").strip()
        application = Application.query.get(application_id) if application_id.isdigit() else None

        if application is None:
            flash("Enter a valid application number.")
        elif application.status != "Approved for inspection":
            flash("That application isn't in 'Approved for inspection' status, so there's no inspection clock to move.")
        else:
            try:
                offset = int(days_ago)
            except ValueError:
                offset = 0
            application.inspection_requested_at = datetime.now(timezone.utc) - timedelta(days=offset)
            db.session.commit()
            flash(f"Application #{application.id}'s inspection clock is now {offset} day(s) old. Run the SLA check to see the effect.")

    applications = (
        Application.query.filter_by(status="Approved for inspection")
        .order_by(Application.id).all()
    )
    return render_template("admin_testing_tools.html", applications=applications)


@admin_bp.route("/application/<int:application_id>")
@admin_required
def application_detail(application_id):
    application = Application.query.get_or_404(application_id)
    photos = (
        InspectionPhoto.query.filter_by(application_id=application_id)
        .order_by(InspectionPhoto.uploaded_at.desc())
        .all()
    )
    return render_template(
        "detail.html", application=application, photos=photos,
        ssn_masked=mask_ssn(application.ssn),
    )


@admin_bp.route("/application/<int:application_id>/decide", methods=["POST"])
@admin_required
def decide(application_id):
    application = Application.query.get_or_404(application_id)
    decision = request.form.get("decision")

    if decision == "ApproveForInspection":
        if application.status not in ("Pending", "Active — unit available", "Waitlisted"):
            flash("This application isn't in a stage where it can be approved for inspection.")
            return redirect(url_for("admin.application_detail", application_id=application_id))

        application.status = "Approved for inspection"
        application.inspection_status = "Scheduled"
        application.inspection_requested_at = datetime.now(timezone.utc)
        db.session.commit()

        pm = application.property.assignments[0].user if application.property.assignments else None
        if pm:
            sent, error = mail.send_inspection_assigned_email(application, pm)
            flash(f"Approved for inspection. {'PM notified.' if sent else 'PM notification not sent: ' + str(error)}")
        else:
            flash("Approved for inspection, but no property manager is assigned to this property to notify.")
        return redirect(url_for("admin.application_detail", application_id=application_id))

    if decision not in ("Approved", "Denied"):
        return redirect(url_for("admin.application_detail", application_id=application_id))

    application.status = decision
    application.decision_date = date.today()
    db.session.commit()

    sent, error = mail.send_decision_email(application)
    if sent:
        flash(f"Application {decision.lower()}. Email sent to {application.email}.")
    else:
        flash(f"Application {decision.lower()}. Email was not sent: {error}")

    return redirect(url_for("admin.application_detail", application_id=application_id))
