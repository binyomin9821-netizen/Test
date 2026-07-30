from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from tenant_app import db
from tenant_app.models import Application, InspectionPhoto
from tenant_app.s3_utils import upload_inspection_photo

inspector_bp = Blueprint("inspector", __name__, url_prefix="/inspector")


def _require_inspector():
    if current_user.role not in ("inspector", "decision_maker"):
        abort(403)


@inspector_bp.route("/dashboard")
@login_required
def dashboard():
    _require_inspector()
    pending_applications = (
        Application.query.filter_by(status="pending").order_by(Application.created_at.asc()).all()
    )
    return render_template("inspector_dashboard.html", applications=pending_applications)


@inspector_bp.route("/applications/<int:application_id>/upload", methods=["POST"])
@login_required
def upload_photo(application_id):
    _require_inspector()
    application = Application.query.get_or_404(application_id)

    file_storage = request.files.get("photo")
    if not file_storage or not file_storage.filename:
        flash("Please choose a photo to upload.", "error")
        return redirect(url_for("inspector.dashboard"))

    try:
        bucket, key = upload_inspection_photo(file_storage, application.id)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("inspector.dashboard"))

    photo = InspectionPhoto(
        application_id=application.id,
        s3_bucket=bucket,
        s3_key=key,
        uploaded_by_id=current_user.id,
    )
    db.session.add(photo)
    db.session.commit()

    flash(f"Photo uploaded for application #{application.id}.", "success")
    return redirect(url_for("inspector.dashboard"))
