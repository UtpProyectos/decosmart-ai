"""APScheduler (BackgroundScheduler): resumen diario, expirar cotizaciones (cada hora), limpiar fotos (diario).

Solo arranca si SCHEDULER_ENABLED y APP_ENV != test. Lo registra `app.api.admin.register(app)`.
"""

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.timeutil import now_utc
from app.models import Simulation
from app.services.errors import log_error

log = logging.getLogger(__name__)
_scheduler = None


def cleanup_photos(db: Session) -> int:
    """Borra del storage las fotos de entrada (Simulation.input_key) más antiguas que PHOTO_RETENTION_DAYS."""
    from app.storage import get_storage

    cutoff = now_utc() - timedelta(days=get_settings().photo_retention_days)
    storage = get_storage()
    sims = db.scalars(select(Simulation).where(Simulation.input_key.is_not(None), Simulation.created_at < cutoff)).all()
    deleted = 0
    for sim in sims:
        try:
            storage.delete(sim.input_key)
            sim.input_key = None
            deleted += 1
        except Exception as exc:  # noqa: BLE001
            log_error(db, "storage", exc.__class__.__name__, str(exc), {"simulation_id": sim.id}, commit=False)
    db.commit()
    return deleted


def _run_job(name: str, fn) -> None:
    with SessionLocal() as db:
        try:
            result = fn(db)
            log.info("Job %s: %s", name, result)
        except Exception as exc:  # noqa: BLE001
            log.exception("Job %s falló", name)
            db.rollback()
            log_error(db, "automation", exc.__class__.__name__, str(exc), {"job": name})


def job_daily_summary() -> None:
    from app.automation.summary import send_daily_summary

    _run_job("daily_summary", send_daily_summary)


def job_expire_quotes() -> None:
    from app.services.quotes import expire_quotes

    _run_job("expire_quotes", expire_quotes)


def job_cleanup_photos() -> None:
    _run_job("cleanup_photos", cleanup_photos)


def build_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler

    s = get_settings()
    sched = BackgroundScheduler(timezone=s.timezone)
    sched.add_job(job_daily_summary, "cron", hour=s.daily_summary_hour, minute=0, id="daily_summary",
                  replace_existing=True, misfire_grace_time=3600, coalesce=True)
    sched.add_job(job_expire_quotes, "interval", hours=1, id="expire_quotes", replace_existing=True, coalesce=True)
    sched.add_job(job_cleanup_photos, "cron", hour=3, minute=30, id="cleanup_photos", replace_existing=True,
                  misfire_grace_time=3600, coalesce=True)
    return sched


def should_start() -> bool:
    s = get_settings()
    return s.scheduler_enabled and s.app_env != "test"


def start() -> None:
    global _scheduler
    if _scheduler is not None or not should_start():
        return
    _scheduler = build_scheduler()
    _scheduler.start()
    log.info("Scheduler iniciado (%s)", get_settings().timezone)


def stop() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
