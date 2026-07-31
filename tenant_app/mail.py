"""
Sends the tenant a short email when the decision-maker approves or denies
their application. Uses Gmail's outgoing mail server and Python's
built-in email tools, so no extra packages are needed.

If EMAIL_ENABLED is False in config (see .env.example), sending is
skipped and this just reports back that it's turned off -- Approve/Deny
still work either way.
"""
import smtplib
from email.message import EmailMessage

from tenant_app import config


def send_decision_email(to_email, full_name, property_name, status, application_id):
    """Returns (True, None) on success, or (False, message) if it didn't send."""
    if not config.EMAIL_ENABLED:
        return False, "Email notifications are turned off (see .env)."

    message = EmailMessage()
    message["Subject"] = f"Update on your application to {property_name}"
    message["From"] = f"{config.EMAIL_FROM_NAME} <{config.EMAIL_ADDRESS}>"
    message["To"] = to_email
    message.set_content(
        f"Hello {full_name},\n\n"
        f"There's an update on your application (reference #{application_id}) "
        f"to {property_name}.\n\n"
        f"Status: {status}\n\n"
        f"If you have questions, please contact the property directly.\n"
    )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
            server.send_message(message)
        return True, None
    except Exception as exc:
        return False, str(exc)
