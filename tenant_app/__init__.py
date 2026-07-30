import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(app.instance_path, "tenant_app.db")
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB upload cap

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from tenant_app import models
    from tenant_app.routes_public import public_bp
    from tenant_app.routes_auth import auth_bp
    from tenant_app.routes_inspector import inspector_bp
    from tenant_app.routes_admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(inspector_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    with app.app_context():
        db.create_all()

    return app
