"""
The data model for the tenant-application system.

Notes on some choices, for future-you:
- Status/role fields are plain strings (with the allowed values documented
  in a comment next to each column) rather than native Postgres ENUM
  types. Postgres ENUMs are awkward to extend later (adding a new value
  needs its own migration step); a plain column with app-level checks is
  simpler to grow across the phases still to come.
- Money is Numeric, never Float -- Float loses precision on dollar
  amounts.
- There is deliberately no disability/accommodation field anywhere in
  this model. That was scoped for Phase 2 but held back pending legal
  review, per an explicit decision -- don't add it without checking.

Application lifecycle (the `status` column):
  Active — unit available  \\
  Waitlisted                >  intake stage, set automatically by Unit
  Pending (legacy)          /   vacancy at the moment the application
                                is created (see routes_intake.py)
       |
       v  admin clicks "Approve for Inspection"
  Approved for inspection  --  notifies the assigned PM, starts the
                                5-day inspection SLA (Phase 4)
       |
       v  PM completes the inspection (Phase 5) -- admin reviews it
  Approved  /  Denied           <- terminal
"""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from tenant_app.crypto import EncryptedString
from tenant_app.extensions import db

ROLES = ("admin", "property_manager")

INTAKE_STATUSES = ("Pending", "Active — unit available", "Waitlisted")
APPLICATION_STATUSES = INTAKE_STATUSES + ("Approved for inspection", "Approved", "Denied")

UNIT_STATUSES = ("vacant", "occupied")
INSPECTION_STATUSES = ("Scheduled", "Completed", "Overdue")

SCORE_CRITERIA = (
    ("score_cleanliness", "Overall cleanliness"),
    ("score_clutter", "Clutter / organization level"),
    ("score_kitchen", "Kitchen condition (appliances, cabinets, fridge contents)"),
    ("score_bathroom", "Bathroom condition"),
    ("score_structural", "Structural condition (walls, floors, ceilings)"),
    ("score_safety", "Safety (smoke detectors, locks, visible hazards)"),
    ("score_odor", "Odor"),
    ("score_pests", "Pest evidence"),
    ("score_utilities", "Utilities working (plumbing, electrical, heat/AC)"),
    ("score_move_in_readiness", "Overall move-in readiness"),
)

MIN_INSPECTION_PHOTOS = 10
MAX_INSPECTION_PHOTOS = 15


def _utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """An admin or property-manager login. Applicants never get a row here
    -- there's no applicant self-login, by design."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'property_manager'

    # Used by Phase 4 to escalate an overdue inspection past the PM.
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

    @property
    def vacant_unit_count(self):
        return sum(1 for u in self.units if u.status == "vacant")

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

    # Basic info
    full_name = db.Column(db.String(200), nullable=False)
    date_of_birth = db.Column(db.Date)
    ssn_encrypted = db.Column(EncryptedString)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    current_address = db.Column(db.String(400), nullable=False)

    # Household info
    marital_status = db.Column(db.String(50))
    number_of_children = db.Column(db.Integer)

    # Employment / income (Phase 2)
    employer_name = db.Column(db.String(200))
    employer_contact = db.Column(db.String(200))
    income_employment = db.Column(db.Numeric(10, 2))
    income_benefits = db.Column(db.Numeric(10, 2))
    income_other = db.Column(db.Numeric(10, 2))

    # Consent (Phase 2) -- the applicant's own signed paper form is the
    # actual legal record; this just mirrors what was written on it.
    signature_name = db.Column(db.String(200))
    consent_given = db.Column(db.Boolean, default=False)

    # Decision-maker workflow -- see the module docstring for the full
    # lifecycle. 'Waitlisted' / 'Active — unit available' are set
    # automatically at intake (Phase 3); everything past that is manual.
    status = db.Column(db.String(30), nullable=False, default="Pending")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    decision_date = db.Column(db.Date)

    # Waitlist ordering (Phase 3). Default order is FCFS by created_at;
    # this flag lets an admin bump someone ahead of that, but only ever
    # alongside a WaitlistOverride row recording who did it and why.
    waitlist_prioritized = db.Column(db.Boolean, nullable=False, default=False)

    # The scanned paper application (Phase 2).
    paper_form_photo_path = db.Column(db.String(500))
    ocr_extracted_text = db.Column(db.Text)

    # Inspection workflow (Phase 4/5).
    inspection_status = db.Column(db.String(20))  # 'Scheduled' / 'Completed' / 'Overdue'
    inspection_requested_at = db.Column(db.DateTime(timezone=True))

    # NOTE: every @property below must stay ABOVE the `property =
    # db.relationship(...)` line further down. Assigning to a name
    # `property` inside a class body shadows Python's built-in
    # `property` decorator for the rest of that class body -- any
    # `@property` written after that line silently breaks (it decorates
    # with a SQLAlchemy relationship object instead of the real thing,
    # and the class fails to import at all). Found this the hard way.

    @property
    def ssn(self):
        return self.ssn_encrypted

    @ssn.setter
    def ssn(self, value):
        self.ssn_encrypted = value

    @property
    def total_household_income(self):
        return sum(v for v in (self.income_employment, self.income_benefits, self.income_other) if v is not None)

    @property
    def status_css_class(self):
        """A few status values (e.g. 'Active — unit available') have
        spaces/punctuation that can't be used directly as a CSS class --
        this maps every status to a safe, styled one."""
        return {
            "Pending": "pending",
            "Active — unit available": "active",
            "Waitlisted": "waitlisted",
            "Approved for inspection": "inspection",
            "Approved": "approved",
            "Denied": "denied",
        }.get(self.status, "pending")

    @property
    def inspection_days_elapsed(self):
        if self.inspection_requested_at is None:
            return None
        return (_utcnow() - self.inspection_requested_at).days

    @property
    def inspection_days_left(self):
        elapsed = self.inspection_days_elapsed
        if elapsed is None:
            return None
        return 5 - elapsed

    property = db.relationship("Property", back_populates="applications")
    household_members = db.relationship(
        "HouseholdMember", back_populates="application", cascade="all, delete-orphan",
        order_by="HouseholdMember.id",
    )
    inspection_slot = db.relationship(
        "InspectionSlot", back_populates="application", uselist=False
    )
    inspection_photos = db.relationship(
        "InspectionPhoto", back_populates="application", cascade="all, delete-orphan",
        order_by="InspectionPhoto.uploaded_at",
    )
    inspection_submission = db.relationship(
        "InspectionSubmission", back_populates="application", uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Application {self.id} {self.full_name} ({self.status})>"


class HouseholdMember(db.Model):
    """A household member listed on the application, other than the
    applicant themselves."""

    __tablename__ = "household_members"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    date_of_birth = db.Column(db.Date)
    relationship_to_applicant = db.Column(db.String(100))

    application = db.relationship("Application", back_populates="household_members")


class WaitlistOverride(db.Model):
    """Audit trail entry: every time an admin bumps someone ahead on a
    waitlist, or otherwise overrides the default first-come-first-served
    order, it's logged here with a required reason. Never a silent
    change -- this table is the compliance record if that's ever
    questioned."""

    __tablename__ = "waitlist_overrides"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    performed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    application = db.relationship("Application")
    performed_by = db.relationship("User")


class InspectionSlot(db.Model):
    """An available inspection time an applicant can self-book from the
    status page. application_id stays NULL until then. (Phase 4 adds a
    second, admin-triggered way an inspection gets started -- this
    self-booking path still works independently of that.)"""

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


class InspectionSubmission(db.Model):
    """The property manager's completed inspection: 10 scored criteria
    (1-10 each), a description, and an optional voice note. Photos are
    tracked separately in InspectionPhoto (there are several per
    inspection); this is the one-per-application scoring record."""

    __tablename__ = "inspection_submissions"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), unique=True, nullable=False
    )
    submitted_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    score_cleanliness = db.Column(db.Integer, nullable=False)
    score_clutter = db.Column(db.Integer, nullable=False)
    score_kitchen = db.Column(db.Integer, nullable=False)
    score_bathroom = db.Column(db.Integer, nullable=False)
    score_structural = db.Column(db.Integer, nullable=False)
    score_safety = db.Column(db.Integer, nullable=False)
    score_odor = db.Column(db.Integer, nullable=False)
    score_pests = db.Column(db.Integer, nullable=False)
    score_utilities = db.Column(db.Integer, nullable=False)
    score_move_in_readiness = db.Column(db.Integer, nullable=False)

    description = db.Column(db.Text)
    voice_note_path = db.Column(db.String(500))

    application = db.relationship("Application", back_populates="inspection_submission")
    submitted_by = db.relationship("User")

    @property
    def scores(self):
        """[(label, value), ...] in display order, for the admin review page."""
        return [(label, getattr(self, key)) for key, label in SCORE_CRITERIA]

    @property
    def average_score(self):
        values = [v for _, v in self.scores if v is not None]
        return round(sum(values) / len(values), 1) if values else None


class NotificationLog(db.Model):
    """Every notification the system has sent (or tried to send), for the
    audit trail Phase 4 asked for -- e.g. to answer "was the PM actually
    notified" if that's ever disputed."""

    __tablename__ = "notification_logs"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    channel = db.Column(db.String(20), nullable=False, default="email")
    recipient_email = db.Column(db.String(255), nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    success = db.Column(db.Boolean, nullable=False)
    error_message = db.Column(db.Text)

    application = db.relationship("Application")
