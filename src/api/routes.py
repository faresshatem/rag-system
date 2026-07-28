from fastapi import APIRouter, Depends, HTTPException, status, Request, File, Form, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
import tempfile
import os
import shutil
import uuid
from src.ingestion.doc_loader import DocumentLoader
from src.ingestion.chunker import DocumentChunker
from src.ingestion.embedding import EmbeddingGenerator
from src.ingestion.db_connector import QdrantConnector
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
        "tasks": [],
        "query_intent": None,
        "next_agent": None,
        "current_task_id": None
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
def ingest_data(
    domain: str = Form(...),
    file: UploadFile = File(...),
    user_context: dict = Depends(get_current_user_context)
):
    """
    Task 4 boundary applied to data uploading/ingestion.
    Ensures an HR employee cannot upload documents into the IT namespace.
    Restricts data ingestion strictly to Admin users.

    Pipeline: load -> chunk -> embed -> upload to Qdrant -> verify.
    """
    role = user_context.get("role")
    if role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Only Administrators can perform Data Ingestion."
        )

    allowed_domains = user_context.get("domains", [])
    if domain not in allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Write Access Denied: Target namespace {domain} is not in your allowed domains."
        )

    # 1. Save uploaded file temporarily
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name

        # 2. Load document
        docs = DocumentLoader.load(temp_file_path)
        os.remove(temp_file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load file: {str(e)}"
        )

    if not docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No content extracted from {file.filename}."
        )

    # 3. Chunk documents
    document_id = str(uuid.uuid4())
    chunker = DocumentChunker()
    chunks = chunker.chunk(
        docs,
        document_id=document_id,
        domain=domain,
        file_name=file.filename,
    )

    # 4. Map metadata for retrieval layer compatibility
    for chunk in chunks:
        chunk.metadata["document_name"] = chunk.metadata.pop("file_name", file.filename)
        chunk.metadata["source"] = "ingestion_api"
        chunk.metadata["document_type"] = os.path.splitext(file.filename)[1].lower()

    # 5. Generate embeddings
    embedder = EmbeddingGenerator()
    vectors = embedder.embed_documents(chunks)

    # 6. Upload to Qdrant
    connector = QdrantConnector()
    if not connector.collection_exists():
        connector.create_collection(vector_size=len(vectors[0]))
    connector.upload_documents(vectors, chunks)

    # 7. Verify upload by checking points_count
    collection_info = connector.client.get_collection(connector.collection_name)
    points_count = collection_info.points_count

    return {
        "status": "success",
        "message": f"Ingested {file.filename} into namespace: {domain}",
        "chunks_uploaded": len(chunks),
        "qdrant_points_count": points_count,
    }