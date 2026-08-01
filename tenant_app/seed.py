"""
Sets up the database tables the first time the app runs, creates the
bootstrap admin login if none exists yet, and fills in sample data (only
when the properties table is empty) so there's something to look at
right away. Safe to call every time the app starts.
"""
from datetime import date, datetime, timedelta, timezone

from tenant_app import config
from tenant_app.extensions import db
from tenant_app.models import (
    Application, InspectionSlot, Property, PropertyAssignment, Unit, User,
)


def ensure_database():
    db.create_all()
    _ensure_admin_user()

    if Property.query.count() == 0:
        _add_sample_data()


def _ensure_admin_user():
    if User.query.filter_by(role="admin").first() is not None:
        return
    admin = User(name="Admin", email=config.ADMIN_EMAIL.lower(), role="admin")
    admin.set_password(config.ADMIN_BOOTSTRAP_PASSWORD)
    db.session.add(admin)
    db.session.commit()


def _add_sample_data():
    properties = [
        Property(name="Maple Court Apartments", address="123 Maple St, Springfield",
                  manager_email="manager.maplecourt@example.com", manager_phone="555-020-1000"),
        Property(name="Riverside Commons", address="456 River Rd, Springfield",
                  manager_email="manager.riverside@example.com", manager_phone="555-020-2000"),
        Property(name="Oakwood Terrace", address="789 Oak Ave, Springfield",
                  manager_email="manager.oakwood@example.com", manager_phone="555-020-3000"),
        Property(name="Sunset Gardens", address="321 Sunset Blvd, Springfield",
                  manager_email="manager.sunsetgardens@example.com", manager_phone="555-020-4000"),
        Property(name="Birchwood Homes", address="654 Birch Ln, Springfield",
                  manager_email="manager.birchwood@example.com", manager_phone="555-020-5000"),
    ]
    db.session.add_all(properties)
    db.session.commit()

    for property_ in properties:
        for n in range(1, 5):
            db.session.add(Unit(
                property_id=property_.id, unit_number=f"{n}0{n}",
                status="vacant" if n == 1 else "occupied",
            ))
    db.session.commit()

    pm1 = User(
        name="Pat Rivera", email="pat.rivera@example.com", role="property_manager",
        supervisor_email="supervisor@example.com",
    )
    pm1.set_password("changeme456")
    pm2 = User(name="Sam Chen", email="sam.chen@example.com", role="property_manager")
    pm2.set_password("changeme456")
    db.session.add_all([pm1, pm2])
    db.session.commit()

    db.session.add_all([
        PropertyAssignment(user_id=pm1.id, property_id=properties[0].id),
        PropertyAssignment(user_id=pm1.id, property_id=properties[1].id),
        PropertyAssignment(user_id=pm2.id, property_id=properties[2].id),
        PropertyAssignment(user_id=pm2.id, property_id=properties[3].id),
    ])
    db.session.commit()

    applications = [
        Application(property_id=properties[0].id, full_name="Jordan Alvarez",
                    phone="555-010-1234", email="jordan.alvarez@example.com",
                    current_address="44 Elm St, Springfield", marital_status="Single",
                    number_of_children=0, status="Pending"),
        Application(property_id=properties[1].id, full_name="Priya Natarajan",
                    phone="555-010-5678", email="priya.n@example.com",
                    current_address="89 Cedar Ave, Springfield", marital_status="Married",
                    number_of_children=2, status="Approved"),
        Application(property_id=properties[2].id, full_name="Marcus Webb",
                    phone="555-010-9012", email="marcus.webb@example.com",
                    current_address="17 Pine Rd, Springfield", marital_status="Divorced",
                    number_of_children=1, status="Denied"),
        # Approved for inspection, assigned to Pat Rivera (Maple Court) --
        # for trying out the Phase 4 SLA countdown/reminders right away.
        # See "Testing the inspection SLA" in README.md.
        Application(property_id=properties[0].id, full_name="Dana Kim",
                    phone="555-010-3456", email="dana.kim@example.com",
                    current_address="200 Willow Way, Springfield", marital_status="Single",
                    number_of_children=0, status="Approved for inspection",
                    inspection_status="Scheduled"),
    ]
    db.session.add_all(applications)
    db.session.commit()

    applications[1].decision_date = date(2026, 7, 15)
    applications[2].decision_date = date(2026, 7, 20)
    applications[3].inspection_requested_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.session.commit()

    # Matches the format the "Date and Time" field on the admin Inspection
    # Slots page produces (YYYY-MM-DDTHH:MM, 24-hour), so sample slots
    # sort correctly alongside slots added later through the app.
    db.session.add_all([
        InspectionSlot(slot_time="2026-08-05T10:00"),
        InspectionSlot(slot_time="2026-08-05T14:00"),
        InspectionSlot(slot_time="2026-08-06T09:30"),
    ])
    db.session.commit()
