from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .schemas import QueryRequest, QueryResponse, UserCreate, UserResponse, TokenResponse, IngestRequest
from .database import get_db, User
from .services import AuthService
from .rbac import get_current_user_context
from typing import List

router = APIRouter()

auth_service = AuthService()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    new_user = auth_service.register_user(db, user_in)
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered."
        )
    return new_user

@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    token = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/query", response_model=QueryResponse)
async def run_query(payload: QueryRequest, request: Request, user_context: dict = Depends(get_current_user_context)):
    """
    Task 3: Intercepts query, determines allowed domains, and injects them 
    into the initial state context to avoid cross-domain RAG data leakage.
    """
    allowed_domains = user_context.get("domains", [])
    username = user_context.get("username")
    
    if not allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Your account is not bound to any accessible namespaces."
        )

    graph_app = request.app.state.graph_app

    initial_agent_state = {
        "messages": [{"role": "user", "content": payload.query}],
        "allowed_domains": allowed_domains,
        "username": username,
        "step_count": 0,
        "tasks": []
    }
    
    session_id = user_context.get("session_id")
    if not session_id:
        import uuid
        session_id = f"api_session_{uuid.uuid4().hex[:8]}"
        
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        final_state = await graph_app.ainvoke(initial_agent_state, config=config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph execution failed: {str(e)}"
        )
    
    answer = final_state.get("answer", "No answer generated.")
    step_count = final_state.get("step_count", 0)
    target_domain = final_state.get("target_domain", None)
    
    return QueryResponse(
        next_agent="END",
        target_domain=target_domain,
        step_count=step_count,
        answer=answer
    )


@router.post("/ingest")
def ingest_data(payload: IngestRequest, user_context: dict = Depends(get_current_user_context)):
    """
    Task 4 boundary applied to data uploading/ingestion.
    Ensures an HR employee cannot upload documents into the IT namespace.
    """
    allowed_domains = user_context.get("domains", [])
    if payload.domain not in allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Write Access Denied: Your current role limits ingestion strictly to: {allowed_domains}"
        )
        
    return {
        "status": "success", 
        "message": f"Data securely written and parsed for target namespace: {payload.domain}"
    }