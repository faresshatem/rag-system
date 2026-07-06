from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Multi-User Multi-Domain Agentic RAG System")

class QueryRequest(BaseModel):
    query: str
    auth_token: str

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/query")
def query_endpoint(request: QueryRequest):
    return {
        "status": "success",
        "query": request.query,
        "message": "This is a mock response from the RAG system."
    }
