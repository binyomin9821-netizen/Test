import os

from flask import Flask, send_from_directory
from flask_login import login_required

from tenant_app import config
from tenant_app.extensions import db, login_manager


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(os.path.join(app.instance_path, "uploads"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from tenant_app.auth import auth_bp
    from tenant_app.routes_admin import admin_bp
    from tenant_app.routes_intake import intake_bp
    from tenant_app.routes_pm import pm_bp
    from tenant_app.routes_public import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(pm_bp)
    app.register_blueprint(intake_bp)

    @app.route("/uploads/<path:filename>")
    @login_required
    def uploaded_file(filename):
        return send_from_directory(os.path.join(app.instance_path, "uploads"), filename)

    return app
