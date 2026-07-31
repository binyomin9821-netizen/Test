"""
The tenant application pilot: a public form applicants fill out, and a
password-protected page where the decision-maker reviews and approves or
denies each application. Everything is stored in one SQLite file
(instance/app.db) -- no separate database to install.
"""
import os
import time
from functools import wraps

from flask import (
    Flask, flash, g, redirect, render_template, request, send_from_directory,
    session, url_for,
)
from werkzeug.utils import secure_filename

import config
import mail
from seed import ensure_database, get_connection

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "uploads")
ALLOWED_PHOTO_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "heic"}


def get_db():
    if "db" not in g:
        g.db = get_connection()
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


def inspector_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_inspector"):
            return redirect(url_for("inspector_login"))
        return view(*args, **kwargs)

    return wrapped


def allowed_photo(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS


# ---------------------------------------------------------------------------
# Public: tenant application form
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("apply"))


@app.route("/apply", methods=["GET", "POST"])
def apply():
    db = get_db()
    properties = db.execute("SELECT id, name, address FROM properties ORDER BY name").fetchall()

    if request.method == "POST":
        errors = []
        property_id = request.form.get("property_id", "").strip()
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        current_address = request.form.get("current_address", "").strip()
        marital_status = request.form.get("marital_status", "").strip()
        number_of_children = request.form.get("number_of_children", "").strip()

        valid_property_ids = {str(p["id"]) for p in properties}
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
            return render_template(
                "apply.html",
                properties=properties,
                errors=errors,
                form=request.form,
            )

        cursor = db.execute(
            """INSERT INTO applications
               (property_id, full_name, phone, email, current_address,
                marital_status, number_of_children)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (property_id, full_name, phone, email, current_address,
             marital_status or None, children_value),
        )
        db.commit()
        return redirect(url_for("confirmation", application_id=cursor.lastrowid))

    return render_template("apply.html", properties=properties, errors=[], form={})


@app.route("/confirmation/<int:application_id>")
def confirmation(application_id):
    db = get_db()
    application = db.execute(
        """SELECT applications.*, properties.name AS property_name
           FROM applications JOIN properties ON properties.id = applications.property_id
           WHERE applications.id = ?""",
        (application_id,),
    ).fetchone()
    if application is None:
        return redirect(url_for("apply"))
    return render_template("confirmation.html", application=application)


def _find_application(db, reference, email):
    return db.execute(
        """SELECT applications.id, applications.status, applications.created_at,
                  applications.decision_date, applications.inspection_status,
                  properties.name AS property_name
           FROM applications JOIN properties ON properties.id = applications.property_id
           WHERE applications.id = ? AND lower(applications.email) = lower(?)""",
        (reference, email),
    ).fetchone()


@app.route("/status", methods=["GET", "POST"])
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
            db = get_db()
            application = _find_application(db, reference, email)
            if application is None:
                error = "We couldn't find an application with that reference number and email."
            else:
                if slot_id:
                    result = db.execute(
                        "UPDATE inspection_slots SET application_id = ? WHERE id = ? AND application_id IS NULL",
                        (application["id"], slot_id),
                    )
                    if result.rowcount:
                        db.execute(
                            "UPDATE applications SET inspection_status = 'Scheduled' WHERE id = ?",
                            (application["id"],),
                        )
                        db.commit()
                        booked_message = "Your inspection time is booked!"
                        application = _find_application(db, reference, email)
                    else:
                        db.rollback()
                        error = "Sorry, that time slot was just taken. Please pick another."

                my_slot = db.execute(
                    "SELECT slot_time FROM inspection_slots WHERE application_id = ?",
                    (application["id"],),
                ).fetchone()
                if my_slot is None and application["status"] != "Denied":
                    open_slots = db.execute(
                        "SELECT id, slot_time FROM inspection_slots WHERE application_id IS NULL ORDER BY slot_time"
                    ).fetchall()

    return render_template(
        "status.html", application=application, error=error,
        booked_message=booked_message, my_slot=my_slot, open_slots=open_slots,
    )


# ---------------------------------------------------------------------------
# Admin: login
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == config.ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Incorrect password."
    return render_template("login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))


# ---------------------------------------------------------------------------
# Admin: dashboard and application detail
# ---------------------------------------------------------------------------

@app.route("/admin")
@login_required
def admin_dashboard():
    db = get_db()
    applications = db.execute(
        """SELECT applications.id, applications.full_name, applications.status,
                  applications.created_at, properties.name AS property_name
           FROM applications JOIN properties ON properties.id = applications.property_id
           ORDER BY applications.created_at DESC, applications.id DESC"""
    ).fetchall()
    return render_template("dashboard.html", applications=applications)


@app.route("/admin/properties", methods=["GET", "POST"])
@login_required
def admin_properties():
    db = get_db()
    errors = []

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        pm_email = request.form.get("property_manager_email", "").strip()

        if not name:
            errors.append("Please enter a property name.")
        if not address:
            errors.append("Please enter an address.")

        if not errors:
            db.execute(
                "INSERT INTO properties (name, address, property_manager_email) VALUES (?, ?, ?)",
                (name, address, pm_email or None),
            )
            db.commit()
            return redirect(url_for("admin_properties"))

    properties = db.execute(
        """SELECT properties.id, properties.name, properties.address,
                  properties.property_manager_email,
                  COUNT(applications.id) AS total_count,
                  SUM(CASE WHEN applications.status = 'Pending' THEN 1 ELSE 0 END) AS pending_count
           FROM properties
           LEFT JOIN applications ON applications.property_id = properties.id
           GROUP BY properties.id
           ORDER BY properties.name"""
    ).fetchall()
    return render_template("admin_properties.html", properties=properties, errors=errors, form=request.form)


@app.route("/admin/inspections", methods=["GET", "POST"])
@login_required
def admin_inspections():
    db = get_db()

    if request.method == "POST":
        slot_time = request.form.get("slot_time", "").strip()
        if slot_time:
            db.execute("INSERT INTO inspection_slots (slot_time) VALUES (?)", (slot_time,))
            db.commit()
        return redirect(url_for("admin_inspections"))

    slots = db.execute(
        """SELECT inspection_slots.id, inspection_slots.slot_time,
                  applications.id AS application_id, applications.full_name,
                  applications.inspection_status
           FROM inspection_slots
           LEFT JOIN applications ON applications.id = inspection_slots.application_id
           ORDER BY inspection_slots.slot_time"""
    ).fetchall()
    return render_template("admin_inspections.html", slots=slots)


@app.route("/admin/application/<int:application_id>")
@login_required
def admin_application_detail(application_id):
    db = get_db()
    application = db.execute(
        """SELECT applications.*, properties.name AS property_name,
                  properties.address AS property_address
           FROM applications JOIN properties ON properties.id = applications.property_id
           WHERE applications.id = ?""",
        (application_id,),
    ).fetchone()
    if application is None:
        return redirect(url_for("admin_dashboard"))

    photos = db.execute(
        "SELECT id, photo_path, uploaded_at FROM inspection_photos WHERE application_id = ? ORDER BY uploaded_at DESC",
        (application_id,),
    ).fetchall()
    slot = db.execute(
        "SELECT slot_time FROM inspection_slots WHERE application_id = ?",
        (application_id,),
    ).fetchone()
    return render_template("detail.html", application=application, photos=photos, slot=slot)


@app.route("/admin/application/<int:application_id>/decide", methods=["POST"])
@login_required
def admin_decide(application_id):
    new_status = request.form.get("decision")
    if new_status not in ("Approved", "Denied"):
        return redirect(url_for("admin_application_detail", application_id=application_id))

    db = get_db()
    db.execute(
        "UPDATE applications SET status = ?, decision_date = date('now') WHERE id = ?",
        (new_status, application_id),
    )
    db.commit()

    application = db.execute(
        """SELECT applications.full_name, applications.email, properties.name AS property_name
           FROM applications JOIN properties ON properties.id = applications.property_id
           WHERE applications.id = ?""",
        (application_id,),
    ).fetchone()

    sent, error = mail.send_decision_email(
        application["email"], application["full_name"], application["property_name"],
        new_status, application_id,
    )
    if sent:
        flash(f"Application {new_status.lower()}. Email sent to {application['email']}.")
    else:
        flash(f"Application {new_status.lower()}. Email was not sent: {error}")

    return redirect(url_for("admin_application_detail", application_id=application_id))


# ---------------------------------------------------------------------------
# Inspector portal: login, dashboard, uploading photos
# ---------------------------------------------------------------------------

@app.route("/inspector/login", methods=["GET", "POST"])
def inspector_login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == config.INSPECTOR_PASSWORD:
            session["is_inspector"] = True
            return redirect(url_for("inspector_dashboard"))
        error = "Incorrect password."
    return render_template("inspector_login.html", error=error)


@app.route("/inspector/logout")
def inspector_logout():
    session.pop("is_inspector", None)
    return redirect(url_for("inspector_login"))


@app.route("/inspector")
@inspector_required
def inspector_dashboard():
    db = get_db()
    inspections = db.execute(
        """SELECT inspection_slots.slot_time, applications.id AS application_id,
                  applications.full_name, applications.inspection_status,
                  properties.name AS property_name
           FROM inspection_slots
           JOIN applications ON applications.id = inspection_slots.application_id
           JOIN properties ON properties.id = applications.property_id
           ORDER BY inspection_slots.slot_time"""
    ).fetchall()
    return render_template("inspector_dashboard.html", inspections=inspections)


@app.route("/inspector/application/<int:application_id>")
@inspector_required
def inspector_application_detail(application_id):
    db = get_db()
    application = db.execute(
        """SELECT applications.*, properties.name AS property_name,
                  properties.address AS property_address
           FROM applications JOIN properties ON properties.id = applications.property_id
           WHERE applications.id = ?""",
        (application_id,),
    ).fetchone()
    if application is None:
        return redirect(url_for("inspector_dashboard"))

    photos = db.execute(
        "SELECT id, photo_path, uploaded_at FROM inspection_photos WHERE application_id = ? ORDER BY uploaded_at DESC",
        (application_id,),
    ).fetchall()
    return render_template("inspector_detail.html", application=application, photos=photos)


@app.route("/inspector/application/<int:application_id>/upload", methods=["POST"])
@inspector_required
def inspector_upload_photo(application_id):
    db = get_db()
    application = db.execute("SELECT id FROM applications WHERE id = ?", (application_id,)).fetchone()
    if application is None:
        return redirect(url_for("inspector_dashboard"))

    photo = request.files.get("photo")
    if photo and photo.filename and allowed_photo(photo.filename):
        folder = os.path.join(UPLOAD_FOLDER, str(application_id))
        os.makedirs(folder, exist_ok=True)
        safe_name = secure_filename(photo.filename)
        stored_name = f"{int(time.time() * 1000)}_{safe_name}"
        photo.save(os.path.join(folder, stored_name))

        db.execute(
            "INSERT INTO inspection_photos (application_id, photo_path) VALUES (?, ?)",
            (application_id, f"{application_id}/{stored_name}"),
        )
        db.commit()
        flash("Photo uploaded.")
    else:
        flash("Please choose an image file (JPG, PNG, GIF, WEBP, or HEIC).")

    return redirect(url_for("inspector_application_detail", application_id=application_id))


@app.route("/inspector/application/<int:application_id>/complete", methods=["POST"])
@inspector_required
def inspector_mark_complete(application_id):
    db = get_db()
    db.execute(
        "UPDATE applications SET inspection_status = 'Completed' WHERE id = ?",
        (application_id,),
    )
    db.commit()
    flash("Inspection marked complete.")
    return redirect(url_for("inspector_application_detail", application_id=application_id))


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    if not (session.get("is_admin") or session.get("is_inspector")):
        return redirect(url_for("admin_login"))
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    ensure_database()
    app.run(host="127.0.0.1", port=5000, debug=True)
