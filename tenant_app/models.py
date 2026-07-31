"""
The data model for the tenant-application system.

Notes on some choices, for future-you:
- Status/role fields are plain strings (with the allowed values documented
  in a comment next to each column) rather than native Postgres ENUM
  types. Postgres ENUMs are awkward to extend later (adding a new value
  needs its own migration step); a plain column with app-level checks is
  simpler to grow across the phases still to come.
- Money isn't modeled yet (income breakdown comes in Phase 2) -- when it
  is, use Numeric, never Float, for anything that represents dollars.
"""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from tenant_app.extensions import db

ROLES = ("admin", "property_manager")
APPLICATION_STATUSES = ("Pending", "Approved", "Denied", "Waitlisted")
UNIT_STATUSES = ("vacant", "occupied")
INSPECTION_STATUSES = ("Scheduled", "Completed")


def _utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """An admin or property-manager login. Applicants never get a row here
    -- the public application form doesn't require an account."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'property_manager'

    # Phase 4 will use this to notify a PM's supervisor on overdue
    # inspections. Unused until then.
    supervisor_email = db.Column(db.String(255))

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    assignments = db.relationship(
        "PropertyAssignment", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def assigned_property_ids(self):
        return [a.property_id for a in self.assignments]

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Property(db.Model):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(400), nullable=False)
    manager_email = db.Column(db.String(255))
    manager_phone = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    units = db.relationship("Unit", back_populates="property", cascade="all, delete-orphan")
    applications = db.relationship("Application", back_populates="property")
    assignments = db.relationship(
        "PropertyAssignment", back_populates="property", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Property {self.name}>"


class PropertyAssignment(db.Model):
    """Which property-manager users can see which properties. Many-to-many:
    a PM can be assigned multiple properties, and (in principle) a
    property could have more than one PM."""

    __tablename__ = "property_assignments"
    __table_args__ = (db.UniqueConstraint("user_id", "property_id", name="uq_user_property"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)

    user = db.relationship("User", back_populates="assignments")
    property = db.relationship("Property", back_populates="assignments")


class Unit(db.Model):
    __tablename__ = "units"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)
    unit_number = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="occupied")  # 'vacant' or 'occupied'

    property = db.relationship("Property", back_populates="units")


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)

    # Part 1: basic info
    full_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    current_address = db.Column(db.String(400), nullable=False)

    # Part 2: household info
    marital_status = db.Column(db.String(50))
    number_of_children = db.Column(db.Integer)

    # Decision-maker workflow. 'Waitlisted' exists as a valid value now for
    # forward compatibility with Phase 3, but nothing sets it
    # automatically yet -- only Approve/Deny are wired up so far.
    status = db.Column(db.String(20), nullable=False, default="Pending")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    decision_date = db.Column(db.Date)

    # Reserved for Phase 2 (paper application + OCR). Unused for now.
    paper_form_photo_path = db.Column(db.String(500))
    ocr_extracted_text = db.Column(db.Text)

    # Inspection workflow: NULL (not scheduled), 'Scheduled', or 'Completed'.
    inspection_status = db.Column(db.String(20))

    property = db.relationship("Property", back_populates="applications")
    inspection_slot = db.relationship(
        "InspectionSlot", back_populates="application", uselist=False
    )
    inspection_photos = db.relationship(
        "InspectionPhoto", back_populates="application", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Application {self.id} {self.full_name} ({self.status})>"


class InspectionSlot(db.Model):
    """An available inspection time. Set by an admin; booked by an
    applicant on the status page. application_id stays NULL until then."""

    __tablename__ = "inspection_slots"

    id = db.Column(db.Integer, primary_key=True)
    slot_time = db.Column(db.String(50), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), unique=True)

    application = db.relationship("Application", back_populates="inspection_slot")


class InspectionPhoto(db.Model):
    """A photo of the applicant's current home, uploaded by the assigned
    property manager for the admin to review."""

    __tablename__ = "inspection_photos"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    photo_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    application = db.relationship("Application", back_populates="inspection_photos")
