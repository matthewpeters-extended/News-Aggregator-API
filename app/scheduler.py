from apscheduler.schedulers.background import BackgroundScheduler

from app.aggregator import run_aggregation
from app.config import settings
from app.database import SessionLocal

scheduler = BackgroundScheduler()


def _run_aggregation_job():
    db = SessionLocal()
    try:
        run_aggregation(db)
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            _run_aggregation_job,
            "interval",
            minutes=settings.aggregation_interval_minutes,
            id="aggregate_articles",
            replace_existing=True,
        )
        scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
