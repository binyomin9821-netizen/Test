"""Populate the database with a few sample applications and staff logins,
so the Inspector Portal and Decision-Maker views have something to show.

Usage:
    python scripts/seed_sample_data.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tenant_app import create_app, db
from tenant_app.models import Application, User

SAMPLE_APPLICATIONS = [
    dict(
        full_name="Maria Gonzalez",
        phone="555-201-4432",
        email="maria.gonzalez@example.com",
        current_address="118 Maple Street, Apt 3B, Springfield",
        marital_status="Married",
        number_of_children=2,
    ),
    dict(
        full_name="David Chen",
        phone="555-330-9981",
        email="david.chen@example.com",
        current_address="47 Birchwood Ave, Unit 12, Springfield",
        marital_status="Single",
        number_of_children=0,
    ),
    dict(
        full_name="Aisha Thompson",
        phone="555-118-7765",
        email="aisha.thompson@example.com",
        current_address="902 Riverside Drive, Springfield",
        marital_status="Divorced",
        number_of_children=1,
    ),
]

SAMPLE_USERS = [
    dict(username="inspector1", password="Inspector#2026", role="inspector"),
    dict(username="reviewer1", password="Reviewer#2026", role="decision_maker"),
]


def main():
    app = create_app()
    with app.app_context():
        for data in SAMPLE_APPLICATIONS:
            if Application.query.filter_by(email=data["email"]).first():
                continue
            db.session.add(Application(status="pending", **data))

        for data in SAMPLE_USERS:
            if User.query.filter_by(username=data["username"]).first():
                continue
            user = User(username=data["username"], role=data["role"])
            user.set_password(data["password"])
            db.session.add(user)

        db.session.commit()

    print("Sample applications added:")
    for a in SAMPLE_APPLICATIONS:
        print(f"  - {a['full_name']} ({a['current_address']})")
    print("\nStaff logins created:")
    for u in SAMPLE_USERS:
        print(f"  - username: {u['username']}  password: {u['password']}  role: {u['role']}")
    print("\n(Change these sample passwords before using this for real.)")


if __name__ == "__main__":
    main()
