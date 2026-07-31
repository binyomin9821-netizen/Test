# Settings for the pilot. You only need to edit the passwords below (and
# optionally the email settings further down) -- everything else can stay
# as-is.
#
# ADMIN_PASSWORD is the one shared password the decision-maker uses to log
# in and see all applications. Change "changeme123" to whatever you like.
ADMIN_PASSWORD = "changeme123"

# INSPECTOR_PASSWORD is a separate shared password for whoever visits
# tenants' homes and uploads inspection photos. It's a different login
# from the decision-maker's, so inspectors don't see the full dashboard.
INSPECTOR_PASSWORD = "changeme789"

# SECRET_KEY is just a random string Flask uses internally to keep your
# login session secure. Any long random text works. You don't need to
# change this for the pilot.
SECRET_KEY = "pilot-secret-key-change-if-you-want-b7f3d9"

# --- Email notifications (optional) ---
# When EMAIL_ENABLED is True, the app automatically emails a tenant when
# the decision-maker clicks Approve or Deny. Leave it as False to skip
# this entirely -- Approve/Deny still work fine, they just won't email
# anyone. See "Setting up tenant emails" in README.md for how to fill
# these in with a Gmail account.
EMAIL_ENABLED = False
EMAIL_ADDRESS = "you@gmail.com"
EMAIL_APP_PASSWORD = ""
EMAIL_FROM_NAME = "Housing Applications"
