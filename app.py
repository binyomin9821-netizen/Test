"""
The tenant application pilot: a public form applicants fill out, and a
password-protected page where the decision-maker reviews and approves or
denies each application. Everything is stored in one SQLite file
(instance/app.db) -- no separate database to install.
"""
from functools import wraps

from flask import Flask, g, redirect, render_template, request, session, url_for

import config
from seed import ensure_database, get_connection

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY


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
    return render_template("detail.html", application=application)


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
    return redirect(url_for("admin_application_detail", application_id=application_id))


if __name__ == "__main__":
    ensure_database()
    app.run(host="127.0.0.1", port=5000, debug=True)
