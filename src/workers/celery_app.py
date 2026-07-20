import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

celery_app = Celery(
    "rag_system",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

celery_app.autodiscover_tasks(
    [
        "src.workers",
    ]
)