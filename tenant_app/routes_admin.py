from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from tenant_app import db
from tenant_app.models import Application
from tenant_app.s3_utils import generate_presigned_view_url

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _require_decision_maker():
    if current_user.role != "decision_maker":
        abort(403)


@admin_bp.route("/applications")
@login_required
def dashboard():
    _require_decision_maker()
    applications = Application.query.order_by(Application.created_at.desc()).all()
    return render_template("admin_dashboard.html", applications=applications)


@admin_bp.route("/applications/<int:application_id>")
@login_required
def application_detail(application_id):
    _require_decision_maker()
    application = Application.query.get_or_404(application_id)
    photos = [
        {"id": p.id, "url": generate_presigned_view_url(p.s3_bucket, p.s3_key), "uploaded_at": p.uploaded_at}
        for p in application.photos
    ]
    return render_template("admin_application_detail.html", application=application, photos=photos)


@admin_bp.route("/applications/<int:application_id>/decision", methods=["POST"])
@login_required
def set_decision(application_id):
    _require_decision_maker()
    application = Application.query.get_or_404(application_id)
    decision = request.form.get("decision")
    if decision not in ("approved", "denied"):
        abort(400)
    application.status = decision
    db.session.commit()
    flash(f"Application #{application.id} marked {decision}.", "success")
    return redirect(url_for("admin.application_detail", application_id=application.id))
