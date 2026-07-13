from fastapi import FastAPI
from app.schemas import QueryRequest, QueryResponse, IngestRequest

app = FastAPI(title="Multi-Domain Agentic RAG System API")

@app.post("/query", response_model=QueryResponse)
def run_query(payload: QueryRequest):
    # Mocking the Supervisor Agent's initial handoff state
    return {
        "next_agent": "Supervisor",
        "target_domain": None,
        "step_count": 0,
        "answer": "Mocked: Query received successfully."
    }

@app.post("/ingest")
def ingest_data(payload: IngestRequest):
    return {"status": "success", "message": f"Data queued for domain: {payload.domain}"}

@app.get("/domains")
def list_domains():
    return {"domains": ["HR", "IT", "Finance"]}

@app.post("/evaluate")
def evaluate_pipeline():
    return {"status": "success", "metrics": {"faithfulness": 1.0, "relevance": 1.0}}
