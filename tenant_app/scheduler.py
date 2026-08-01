"""
Runs the Phase 4 inspection SLA check on a real hourly schedule,
independent of whether anyone's loaded a dashboard page (which used to
be the only trigger). Runs inside the same process as the web app --
no extra Docker service, no Redis, no Celery needed for a single-process
pilot deployment.

If this app ever runs behind multiple web worker processes (e.g.
gunicorn with workers > 1), each worker would start its own scheduler.
That's still safe -- sla.run_sla_check()'s per-application,
per-notification-type check against NotificationLog prevents duplicate
emails regardless of how many schedulers are ticking -- but at that
point a single dedicated scheduler process (or a small cron container)
would be the cleaner design instead of one per worker.
"""
from apscheduler.schedulers.background import BackgroundScheduler

from tenant_app import config, sla

_scheduler = None


def start(app):
    global _scheduler
    if not config.ENABLE_SCHEDULER or _scheduler is not None:
        return

    def _tick():
        with app.app_context():
            sla.run_sla_check(force=True)

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(_tick, "interval", hours=1, id="inspection_sla_check", replace_existing=True)
    _scheduler.start()
