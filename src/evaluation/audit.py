from datetime import datetime
from pathlib import Path
import json

AUDIT_DIR = Path("logs")
AUDIT_DIR.mkdir(exist_ok=True)

AUDIT_FILE = AUDIT_DIR / "llm_judge_audit.jsonl"


def log_llm_judge(
    question: str,
    answer: str,
    result,
    latency: float,
    model: str,
):

    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "question": question,
        "answer": answer,
        "faithfulness": result.faithfulness,
        "relevance": result.relevance,
        "citation_accuracy": result.citation_accuracy,
        "completeness": result.completeness,
        "hallucination_risk": result.hallucination_risk,
        "overall_score": result.overall_score,
        "reasoning": result.reasoning,
        "latency": latency,
        "model": model,
    }

    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record))
        f.write("\n")