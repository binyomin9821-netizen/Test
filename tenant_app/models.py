import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from tenant_app import db


class Application(db.Model):
    """A tenant's rental application. Part 1 + Part 2 fields land here."""

    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)

    # Part 1: basic info
    full_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    current_address = db.Column(db.String(400), nullable=False)

    # Part 2: household info
    marital_status = db.Column(db.String(50), nullable=True)
    number_of_children = db.Column(db.Integer, nullable=True)

    # Workflow
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending/approved/denied
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # OCR intake audit trail (see scripts/ocr_fill.py) — never silently overwritten
    ocr_raw_text = db.Column(db.Text, nullable=True)
    ocr_needs_review = db.Column(db.Boolean, default=False)

    photos = db.relationship("InspectionPhoto", backref="application", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "phone": self.phone,
            "email": self.email,
            "current_address": self.current_address,
            "marital_status": self.marital_status,
            "number_of_children": self.number_of_children,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class InspectionPhoto(db.Model):
    """A photo of existing housing conditions, stored in S3 and linked to an application."""

    __tablename__ = "inspection_photos"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    s3_bucket = db.Column(db.String(200), nullable=False)
    s3_key = db.Column(db.String(500), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class User(UserMixin, db.Model):
    """Inspector or decision-maker login. Role gates which portal pages are visible."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="inspector")  # inspector/decision_maker

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
