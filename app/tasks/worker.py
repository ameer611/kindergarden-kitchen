from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "kindergarten_kitchen",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.estimates",
        "app.tasks.reports"
    ]
)

# Optional: Configure Celery directly here or use celeryconfig.py
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# This allows the worker to be started directly from this file
if __name__ == "__main__":
    celery_app.start()
