"""
Login/logout for admin and property-manager users, plus the role-based
access decorators every other route module uses. Applicants never touch
this file -- the public application form has no login at all.
"""
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from tenant_app.extensions import login_manager
from tenant_app.models import User

auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_home_for(current_user))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(_home_for(user))
        error = "Incorrect email or password."

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


def _home_for(user):
    return url_for("admin.dashboard" if user.is_admin else "pm.dashboard")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            flash("That page is for admins only.")
            return redirect(url_for("pm.dashboard"))
        return view(*args, **kwargs)

    return wrapped


def pm_required(view):
    """Property managers AND admins can use PM-portal pages -- an admin
    should be able to see anything a PM can."""

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role not in ("admin", "property_manager"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def visible_property_ids(user):
    """None means 'no restriction' (admins see every property). A list
    means the caller must filter queries to just these property IDs."""
    if user.is_admin:
        return None
    return user.assigned_property_ids
