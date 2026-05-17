from celery.schedules import crontab

from app.workers.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "evaluate-alerts-every-minute": {
        "task": "app.workers.tasks.alert_tasks.evaluate_alerts",
        "schedule": 60.0,
    },
    "cleanup-expired-tokens-daily": {
        "task": "app.workers.tasks.alert_tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=2, minute=0),
    },
}
