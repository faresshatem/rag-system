from fastapi import APIRouter, Depends, HTTPException, status
from .schemas import QueryRequest, QueryResponse, IngestRequest
from .rbac import get_current_user_domains
from typing import List

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def run_query(payload: QueryRequest, allowed_domains: List[str] = Depends(get_current_user_domains)):
    """
    Task 3: Intercepts query, determines allowed domains, and injects them 
    into the initial state context to avoid cross-domain RAG data leakage.
    """
    if not allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Your account is not bound to any accessible namespaces."
        )

    initial_agent_state = {
        "next_agent": "Supervisor",
        "target_domain": None,
        "step_count": 0,
        "allowed_domains": allowed_domains,  # Enforced injection path!
        "query": payload.query,
        "answer": None
    }
    
    return initial_agent_state


@router.post("/ingest")
def ingest_data(payload: IngestRequest, allowed_domains: List[str] = Depends(get_current_user_domains)):
    """
    Task 4 boundary applied to data uploading/ingestion.
    Ensures an HR employee cannot upload documents into the IT namespace.
    """
    if payload.domain not in allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Write Access Denied: Your current role limits ingestion strictly to: {allowed_domains}"
        )
        
    return {
        "status": "success", 
        "message": f"Data securely written and parsed for target namespace: {payload.domain}"
    }
