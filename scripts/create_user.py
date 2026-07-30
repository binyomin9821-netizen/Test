"""CLI to create an inspector or decision-maker login.

Usage:
    python scripts/create_user.py --username jane --password '...' --role inspector
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tenant_app import create_app, db
from tenant_app.models import User


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", choices=["inspector", "decision_maker"], default="inspector")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if User.query.filter_by(username=args.username).first():
            print(f"User '{args.username}' already exists.", file=sys.stderr)
            sys.exit(1)

        user = User(username=args.username, role=args.role)
        user.set_password(args.password)
        db.session.add(user)
        db.session.commit()
        print(f"Created {args.role} user '{args.username}'.")


if __name__ == "__main__":
    main()
