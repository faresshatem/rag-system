from .celery_app import celery_app
from .ingestion_tasks import ingest_document_task

__all__ = [
    "celery_app",
    "ingest_document_task",
]