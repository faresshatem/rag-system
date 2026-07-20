from src.workers.celery_app import celery_app
from src.ingestion import ingest_document


@celery_app.task
def ingest_document_task(
    file_path: str,
    domain: str,
    file_name: str,
) -> None:
    """
    Background task for ingesting a document.
    """

    ingest_document(
        file_path=file_path,
        domain=domain,
        file_name=file_name,
    )
    