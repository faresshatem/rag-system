from src.workers.celery_app import celery_app
from src.monitoring.metrics import (
    judge_requests_total,
    judge_latency_seconds,
    judge_last_score,
    judge_faithfulness,
    judge_relevance,
    judge_completeness,
    judge_citation_accuracy,
    judge_hallucination_risk,
)


@celery_app.task(name="monitoring.record_judge_metrics")
def record_judge_metrics(
    overall_score,
    faithfulness,
    relevance,
    completeness,
    citation_accuracy,
    hallucination_risk,
):
    with judge_latency_seconds.time():

        judge_requests_total.inc()

        judge_last_score.set(overall_score)
        judge_faithfulness.set(faithfulness)
        judge_relevance.set(relevance)
        judge_completeness.set(completeness)
        judge_citation_accuracy.set(citation_accuracy)
        judge_hallucination_risk.set(hallucination_risk)

    return {
        "overall_score": overall_score,
        "faithfulness": faithfulness,
    }