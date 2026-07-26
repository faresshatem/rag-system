from celery import Celery

celery_app = Celery(
    "rag_workers",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

celery_app.autodiscover_tasks(
    [
        "src.evaluation",
    ]
)

# Explicitly import worker tasks
import src.evaluation.eval_worker