import logging
from typing import List

from src.agents.state import AgentState, Citation, RetrievedChunk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SynthesisAgent:
    """
    The Synthesis Agent generates the final response for the user based on the
    completed tasks and the retrieved context accumulated in the AgentState.
    """

    def _read_task_summaries(self, state: AgentState) -> List[str]:
        finished_tasks = [t for t in state.tasks if t.status in ("completed", "failed", "skipped")]
        return [str(t.result_summary) for t in finished_tasks if t.result_summary]

    def _build_citations(self, chunks: List[RetrievedChunk]) -> List[Citation]:
        return [
            Citation(
                span=chunk.text[:200],
                source_file=chunk.file_name,
                chunk_id=chunk.chunk_id,
                page=chunk.page,
            )
            for chunk in chunks
        ]

    def synthesize(self, state: AgentState) -> dict:
        logger.info("Starting synthesis process.")

        summaries = self._read_task_summaries(state)
        retrieved_chunks = state.retrieved_context

        if summaries:
            final_answer = "Based on the retrieved policies and database lookups:\n" + "\n\n".join(summaries)
        else:
            final_answer = "I couldn't find any specific answers for your query, but how can I help you generally?"

        citations = self._build_citations(retrieved_chunks) if retrieved_chunks else None

        logger.info("Synthesis completed. %d task summaries, %d citations.", len(summaries), len(citations or []))

        return {
            "next_agent": "END",
            "answer": final_answer,
            "citations": citations,
        }


_synthesis_agent = SynthesisAgent()


def synthesis_node(state: AgentState) -> dict:
    """LangGraph node wrapper around SynthesisAgent.synthesize()."""
    print("\n[Synthesis Agent] Generating final answer from all task results...")
    return _synthesis_agent.synthesize(state)
