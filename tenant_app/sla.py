"""
The Phase 4 inspection SLA check: sends a daily reminder to whoever's
assigned PM for each pending inspection, and escalates to the admin and
that PM's supervisor once 5 calendar days have passed.

There's no real task scheduler wired up in this pass (that'd mean
another Docker service -- a cron container, or Celery+Redis -- which is
more infrastructure than this stage needs). Instead, `run_sla_check()`
is called opportunistically:
  - Automatically, at most once an hour, whenever the admin or PM
    dashboard loads (see routes_admin.py / routes_pm.py).
  - On demand, via the "Run SLA Check Now" button on the admin
    Inspection Slots page.
This is fine for a pilot but isn't a substitute for a real scheduled job
once this runs in production continuously -- flagging that here so it
isn't a surprise later.
"""
from datetime import datetime, timedelta, timezone

from tenant_app import mail
from tenant_app.extensions import db
from tenant_app.models import Application, NotificationLog

SLA_DAYS = 5

_last_run_at = None


def _utcnow():
    return datetime.now(timezone.utc)


def _already_notified_today(application_id, notification_type):
    since = _utcnow() - timedelta(hours=20)  # a bit under 24h so a slightly-late run still counts as "today"
    return (
        NotificationLog.query.filter(
            NotificationLog.application_id == application_id,
            NotificationLog.notification_type == notification_type,
            NotificationLog.sent_at >= since,
        ).first()
        is not None
    )


def run_sla_check(force=False):
    """Returns a summary dict. Safe to call as often as you like --
    reminders/escalations are only sent once per application per day
    thanks to the NotificationLog check above."""
    global _last_run_at

    if not force and _last_run_at is not None and _utcnow() - _last_run_at < timedelta(hours=1):
        return {"skipped": True}
    _last_run_at = _utcnow()

    pending = Application.query.filter(
        Application.status == "Approved for inspection",
        Application.inspection_status != "Completed",
    ).all()

    reminders_sent, escalations_sent = 0, 0

    for application in pending:
        pm = _assigned_pm(application)
        days_elapsed = application.inspection_days_elapsed
        if days_elapsed is None:
            continue

        if days_elapsed >= SLA_DAYS:
            if application.inspection_status != "Overdue":
                application.inspection_status = "Overdue"
                db.session.commit()

            if not _already_notified_today(application.id, "overdue_admin"):
                mail.send_overdue_admin_email(application)
                escalations_sent += 1
            if pm and pm.supervisor_email and not _already_notified_today(application.id, "overdue_supervisor"):
                mail.send_overdue_supervisor_email(application, pm)
                escalations_sent += 1
        elif pm and not _already_notified_today(application.id, "daily_reminder"):
            mail.send_daily_reminder_email(application, pm)
            reminders_sent += 1

    return {"skipped": False, "checked": len(pending), "reminders_sent": reminders_sent, "escalations_sent": escalations_sent}


def _assigned_pm(application):
    if not application.property.assignments:
        return None
    return application.property.assignments[0].user
