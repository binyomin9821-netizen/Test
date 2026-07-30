from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from tenant_app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _redirect_for_role(current_user.role)

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return _redirect_for_role(user.role)
        error = "Invalid username or password."

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


def _redirect_for_role(role):
    if role == "decision_maker":
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("inspector.dashboard"))
