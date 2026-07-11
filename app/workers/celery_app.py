from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "notification_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

# Apply settings
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    # Define beat schedule for periodic reconciliation job
    beat_schedule={
        "reconcile-stuck-pending-notifications": {
            "task": "app.workers.tasks.reconcile_pending_deliveries",
            "schedule": 300.0,  # Run every 5 minutes (300 seconds)
        }
    },
)
