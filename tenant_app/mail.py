"""
All outbound email for the app: applicant decision notices, and the
Phase 4 inspection-SLA notifications (assignment, daily reminders,
overdue escalation to admin + PM supervisor). Uses Gmail's outgoing mail
server and Python's built-in email tools, so no extra packages are
needed.

If EMAIL_ENABLED is False in config (see .env.example), sending is
skipped -- every function here still logs the attempt to NotificationLog
(with success=False), so "did we even try to notify anyone" is always
answerable from the audit trail, not just "did it succeed."

SMS/text notifications were scoped for Phase 4 but deliberately left out
of this pass -- email-only for now, per an explicit decision. Wiring in
a provider like Twilio later would slot in alongside these functions
without changing how they're called.
"""
import smtplib
from email.message import EmailMessage

from tenant_app import config
from tenant_app.extensions import db
from tenant_app.models import NotificationLog


def _send(to_email, subject, body):
    """Returns (True, None) on success, or (False, message) if it didn't send."""
    if not config.EMAIL_ENABLED:
        return False, "Email notifications are turned off (see .env)."
    if not to_email:
        return False, "No recipient email address on file."

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{config.EMAIL_FROM_NAME} <{config.EMAIL_ADDRESS}>"
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
            server.send_message(message)
        return True, None
    except Exception as exc:
        return False, str(exc)


def _send_and_log(application_id, notification_type, to_email, subject, body):
    sent, error = _send(to_email, subject, body)
    db.session.add(NotificationLog(
        application_id=application_id, notification_type=notification_type,
        channel="email", recipient_email=to_email or "(none on file)",
        success=sent, error_message=error,
    ))
    db.session.commit()
    return sent, error


def send_decision_email(application):
    return _send_and_log(
        application.id, "decision", application.email,
        f"Update on your application to {application.property.name}",
        f"Hello {application.full_name},\n\n"
        f"There's an update on your application (reference #{application.id}) "
        f"to {application.property.name}.\n\n"
        f"Status: {application.status}\n\n"
        f"If you have questions, please contact the property directly.\n",
    )


def send_inspection_assigned_email(application, pm):
    return _send_and_log(
        application.id, "inspection_assigned", pm.email,
        f"New inspection assigned: {application.full_name} (#{application.id})",
        f"Hello {pm.name},\n\n"
        f"An application has been approved for inspection at {application.property.name}, "
        f"and it's assigned to you.\n\n"
        f"Applicant: {application.full_name}\n"
        f"Current address to inspect: {application.current_address}\n"
        f"Phone: {application.phone}\n\n"
        f"Please complete the inspection within 5 calendar days. You'll get a daily "
        f"reminder until it's done. Log in to the property manager portal to submit it.\n",
    )


def send_daily_reminder_email(application, pm):
    days_left = application.inspection_days_left
    return _send_and_log(
        application.id, "daily_reminder", pm.email,
        f"Reminder: inspection due for {application.full_name} (#{application.id})",
        f"Hello {pm.name},\n\n"
        f"This is a reminder that the inspection for {application.full_name} "
        f"(application #{application.id}) at {application.property.name} is still pending.\n\n"
        f"Days left before this is overdue: {max(days_left, 0)}\n\n"
        f"Log in to the property manager portal to submit it.\n",
    )


def send_overdue_admin_email(application):
    return _send_and_log(
        application.id, "overdue_admin", config.ADMIN_EMAIL,
        f"OVERDUE: inspection for {application.full_name} (#{application.id})",
        f"The inspection for application #{application.id} ({application.full_name}, "
        f"{application.property.name}) has passed its 5-day deadline without being completed.\n\n"
        f"The assigned property manager's supervisor has also been notified, if one is on file.\n",
    )


def send_overdue_supervisor_email(application, pm):
    return _send_and_log(
        application.id, "overdue_supervisor", pm.supervisor_email,
        f"OVERDUE: {pm.name}'s inspection for {application.full_name} (#{application.id})",
        f"Hello,\n\n"
        f"An inspection assigned to {pm.name} has passed its 5-day deadline without being "
        f"completed: application #{application.id} ({application.full_name}), "
        f"{application.property.name}.\n",
    )


def send_inspection_submitted_email(application):
    return _send_and_log(
        application.id, "inspection_submitted", config.ADMIN_EMAIL,
        f"Inspection ready for review: {application.full_name} (#{application.id})",
        f"The property manager has completed and submitted the inspection for "
        f"application #{application.id} ({application.full_name}, {application.property.name}). "
        f"Log in to review the scores, photos, and notes.\n",
    )
