from flask import Blueprint, redirect, render_template, request, session, url_for

from tenant_app import db
from tenant_app.models import Application

public_bp = Blueprint("public", __name__)

MARITAL_STATUS_OPTIONS = ["Single", "Married", "Divorced", "Widowed", "Separated", "Prefer not to say"]


@public_bp.route("/")
def index():
    return redirect(url_for("public.apply_part1"))


@public_bp.route("/apply/part1", methods=["GET", "POST"])
def apply_part1():
    """Part 1: basic info. Held in session until Part 2 is submitted."""
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        current_address = request.form.get("current_address", "").strip()

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not phone:
            errors.append("Phone is required.")
        if not email or "@" not in email:
            errors.append("A valid email is required.")
        if not current_address:
            errors.append("Current address is required.")

        if errors:
            return render_template("application_part1.html", errors=errors, form=request.form)

        session["application_part1"] = {
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "current_address": current_address,
        }
        return redirect(url_for("public.apply_part2"))

    return render_template("application_part1.html", errors=None, form={})


@public_bp.route("/apply/part2", methods=["GET", "POST"])
def apply_part2():
    """Part 2: household info. Combines with Part 1 session data and saves the row."""
    part1 = session.get("application_part1")
    if not part1:
        return redirect(url_for("public.apply_part1"))

    if request.method == "POST":
        marital_status = request.form.get("marital_status", "").strip()
        number_of_children_raw = request.form.get("number_of_children", "").strip()

        errors = []
        if marital_status and marital_status not in MARITAL_STATUS_OPTIONS:
            errors.append("Please choose a valid marital status.")

        number_of_children = None
        if number_of_children_raw:
            try:
                number_of_children = int(number_of_children_raw)
                if number_of_children < 0:
                    raise ValueError
            except ValueError:
                errors.append("Number of children must be a non-negative whole number.")

        if errors:
            return render_template(
                "application_part2.html",
                errors=errors,
                form=request.form,
                marital_status_options=MARITAL_STATUS_OPTIONS,
            )

        application = Application(
            full_name=part1["full_name"],
            phone=part1["phone"],
            email=part1["email"],
            current_address=part1["current_address"],
            marital_status=marital_status or None,
            number_of_children=number_of_children,
            status="pending",
        )
        db.session.add(application)
        db.session.commit()

        session.pop("application_part1", None)
        return redirect(url_for("public.apply_confirmation", application_id=application.id))

    return render_template(
        "application_part2.html", errors=None, form={}, marital_status_options=MARITAL_STATUS_OPTIONS
    )


@public_bp.route("/apply/confirmation/<int:application_id>")
def apply_confirmation(application_id):
    application = Application.query.get_or_404(application_id)
    return render_template("application_confirmation.html", application=application)
