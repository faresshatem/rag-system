import contextlib
from fastapi import FastAPI
from pydantic import BaseModel
from src.api.routes import router as api_router
from src.agents.graph import build_graph

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing LangGraph Application...")
    graph_app = await build_graph()
    app.state.graph_app = graph_app
    print("LangGraph Application initialized successfully.")
    yield
    # Shutdown
    print("Shutting down...")

app = FastAPI(title="Multi-User Multi-Domain Agentic RAG System", lifespan=lifespan)

app.include_router(api_router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "ok"}

