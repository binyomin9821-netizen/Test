"""
Shared Flask extension instances. Created here (not in __init__.py) so
other modules can import them without circular-import problems.
"""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
