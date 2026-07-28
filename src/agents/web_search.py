import os
import logging
from typing import List, Optional

from langchain_tavily import TavilySearch

from src.agents.state import AgentState, RetrievedChunk, Task

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", 5))
MAX_SUMMARY_CHARS = 500


class WebSearchAgent:
    """
    The Web Search Agent handles tasks that need current, external information
    not covered by the internal HR/IT knowledge base or structured databases
    (general knowledge, current events, external documentation, etc.). It
    queries the public web via Tavily and returns results already shaped into
    AgentState's RetrievedChunk schema, so Verification_Agent and
    Synthesis_Agent treat web results exactly like any other source, with no
    special-casing required downstream.
    """

    def __init__(self, search_tool: TavilySearch):
        self.search_tool = search_tool

    def _generate_query(self, task_description: str) -> str:
        return task_description

    def _convert_to_retrieved_chunks(self, results: List[dict], task_id: str) -> List[RetrievedChunk]:
        chunks = []
        for idx, result in enumerate(results):
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"{task_id}_web_{idx}",
                    file_name=result.get("title") or result.get("url") or "Web result",
                    text=result.get("content") or "",
                    page=None,
                    metadata={
                        "url": result.get("url"),
                        "source": "web_search",
                    },
                    score=result.get("score"),
                )
            )
        return chunks

    def execute(self, task: Task) -> List[RetrievedChunk]:
        """
        Run a live web search for a single task and return the results already
        converted to AgentState's RetrievedChunk schema (mirrors
        RetrievalAgent.execute's contract, so retrieval_node and
        web_search_node can share the exact same downstream handling).
        """
        query = self._generate_query(task.description)

        response = self.search_tool.invoke({"query": query})
        results = response.get("results", []) if isinstance(response, dict) else []
        logger.info("Web search completed with %d result(s).", len(results))

        return self._convert_to_retrieved_chunks(results, task.task_id)


# ---------------------------------------------------------------------------
# Singleton wiring (mirrors retrieval.py's pattern: built once and reused
# across graph invocations rather than re-instantiated per call).
# ---------------------------------------------------------------------------
_web_search_agent: Optional[WebSearchAgent] = None


def _get_web_search_agent() -> WebSearchAgent:
    global _web_search_agent
    if _web_search_agent is None:
        _web_search_agent = WebSearchAgent(
            search_tool=TavilySearch(max_results=DEFAULT_MAX_RESULTS, topic="general")
        )
    return _web_search_agent


def web_search_node(state: AgentState) -> dict:
    """
    LangGraph node wrapper around WebSearchAgent.execute(). Performs a live web
    search for the currently active task and updates the task status / result
    summary and the shared retrieved_context list. Structurally identical to
    retrieval_node so Verification_Agent needs no changes to handle either
    source.
    """
    print("\n[Web Search Agent] Running live web search...")

    active_task = next((t for t in state.tasks if t.task_id == state.current_task_id), None)
    if not active_task:
        logger.warning("No active task found in AgentState for Web_Search_Agent.")
        return {"next_agent": "Verification_Agent"}

    try:
        agent = _get_web_search_agent()
        new_chunks = agent.execute(active_task)
    except Exception as e:
        logger.error("Web search task execution failed: %s", str(e))
        updated_tasks = list(state.tasks)
        for t in updated_tasks:
            if t.task_id == active_task.task_id:
                t.status = "completed"
                t.result_summary = f"Web search failed due to an error: {str(e)}"
        return {
            "tasks": updated_tasks,
            "next_agent": "Verification_Agent",
        }

    updated_tasks = list(state.tasks)
    for t in updated_tasks:
        if t.task_id == active_task.task_id:
            t.status = "completed"
            if new_chunks:
                combined_text = " ".join(chunk.text for chunk in new_chunks)
                summary = combined_text[:MAX_SUMMARY_CHARS]
                t.result_summary = f"Found {len(new_chunks)} web result(s): {summary}"
            else:
                t.result_summary = "No web results found for this task."

    updated_context = list(state.retrieved_context) + new_chunks

    return {
        "tasks": updated_tasks,
        "retrieved_context": updated_context,
        "current_task_id": None,
        "next_agent": "Verification_Agent",
    }