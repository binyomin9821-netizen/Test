"""
The property-manager portal. A PM only ever sees the properties assigned
to them (admins can view this portal too, and see everything -- an admin
should be able to see anything a PM can).

This also carries what used to be a separate "inspector" login: PMs are
who visits an applicant's current home and uploads inspection photos, per
the decision to fold that role into Property Manager for now.
"""
import os
import time

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename

from tenant_app.auth import pm_required, visible_property_ids
from tenant_app.extensions import db
from tenant_app.models import Application, InspectionPhoto, InspectionSlot, Property

pm_bp = Blueprint("pm", __name__, url_prefix="/pm")

ALLOWED_PHOTO_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "heic"}


def allowed_photo(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS


def _application_or_404(application_id):
    """Fetches the application, but 404s if the current PM isn't assigned
    to the property it belongs to (admins can reach any application)."""
    application = Application.query.get_or_404(application_id)
    ids = visible_property_ids(current_user)
    if ids is not None and application.property_id not in ids:
        abort(404)
    return application


@pm_bp.route("/")
@pm_required
def dashboard():
    ids = visible_property_ids(current_user)

    properties_query = Property.query
    if ids is not None:
        properties_query = properties_query.filter(Property.id.in_(ids or [-1]))
    properties = properties_query.order_by(Property.name).all()

    inspections_query = (
        InspectionSlot.query.join(Application)
        .filter(InspectionSlot.application_id.isnot(None))
    )
    if ids is not None:
        inspections_query = inspections_query.filter(Application.property_id.in_(ids or [-1]))
    inspections = inspections_query.order_by(InspectionSlot.slot_time).all()

    return render_template("pm_dashboard.html", properties=properties, inspections=inspections)


@pm_bp.route("/application/<int:application_id>")
@pm_required
def application_detail(application_id):
    application = _application_or_404(application_id)
    photos = (
        InspectionPhoto.query.filter_by(application_id=application_id)
        .order_by(InspectionPhoto.uploaded_at.desc())
        .all()
    )
    return render_template("pm_application_detail.html", application=application, photos=photos)


@pm_bp.route("/application/<int:application_id>/upload", methods=["POST"])
@pm_required
def upload_photo(application_id):
    application = _application_or_404(application_id)

    photo = request.files.get("photo")
    if photo and photo.filename and allowed_photo(photo.filename):
        upload_folder = os.path.join(current_app.instance_path, "uploads")
        folder = os.path.join(upload_folder, str(application.id))
        os.makedirs(folder, exist_ok=True)
        safe_name = secure_filename(photo.filename)
        stored_name = f"{int(time.time() * 1000)}_{safe_name}"
        photo.save(os.path.join(folder, stored_name))

        db.session.add(InspectionPhoto(
            application_id=application.id, photo_path=f"{application.id}/{stored_name}",
        ))
        db.session.commit()
        flash("Photo uploaded.")
    else:
        flash("Please choose an image file (JPG, PNG, GIF, WEBP, or HEIC).")

    return redirect(url_for("pm.application_detail", application_id=application.id))


@pm_bp.route("/application/<int:application_id>/complete", methods=["POST"])
@pm_required
def mark_complete(application_id):
    application = _application_or_404(application_id)
    application.inspection_status = "Completed"
    db.session.commit()
    flash("Inspection marked complete.")
    return redirect(url_for("pm.application_detail", application_id=application.id))
