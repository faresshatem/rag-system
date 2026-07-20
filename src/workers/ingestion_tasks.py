import logging

from src.ingestion.pipeline import ingest_document
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="workers.ingest_document",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def ingest_document_task(
    file_path: str,
    domain: str,
    file_name: str,
):
    """
    Background task that processes a document and stores
    its embeddings in Qdrant.
    """

    logger.info("Starting ingestion for %s", file_name)

    ingest_document(
        file_path=file_path,
        domain=domain,
        file_name=file_name,
    )

    logger.info("Finished ingestion for %s", file_name)

    return {
        "status": "completed",
        "file_name": file_name,
        "domain": domain,
    }