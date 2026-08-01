"""
Settings for the app, read from environment variables. Docker Compose
sets these from the .env file in the project root -- you shouldn't need
to edit this file itself. See .env.example for what each setting does.
"""
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL", "postgresql://tenant_app:tenant_app@localhost:5432/tenant_app"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Used once, to create the very first admin login if the users table is
# empty. Change these in .env before first startup -- after that, log in
# and this value is no longer used for anything.
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
ADMIN_BOOTSTRAP_PASSWORD = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "changeme123")

# Encrypts sensitive fields (currently just SSN) at rest. The fallback
# below is NOT secret -- it's baked into this file -- and is only here so
# the app doesn't crash if you forget to set one. Generate your own real
# key (see README.md "Encryption key") and put it in .env before you
# ever store a real SSN.
FIELD_ENCRYPTION_KEY = os.environ.get(
    "FIELD_ENCRYPTION_KEY", "ZGV2LW9ubHktaW5zZWN1cmUtZmFsbGJhY2sta2V5MzI="
)

# --- Email notifications (optional) ---
# Same as before: off by default, Approve/Deny work either way. See
# README.md "Setting up tenant emails" for how to fill these in.
EMAIL_ENABLED = os.environ.get("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "you@gmail.com")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Housing Applications")

# Runs the inspection SLA check (reminders/escalation) on a real hourly
# clock in the background, in addition to it running opportunistically
# on dashboard loads. Leave this on unless you're running a one-off
# script that imports the app and don't want a background thread started.
ENABLE_SCHEDULER = os.environ.get("ENABLE_SCHEDULER", "true").lower() == "true"
