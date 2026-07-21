from typing import List, Dict, Any
from dataclasses import dataclass
from src.agents.state import AgentState, RetrievedChunk, Task
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SynthesisAgent:
    """
    The Synthesis Agent generates the final response for the user based on the AgentState.
    """

    def synthesize(self, agent_state: AgentState) -> str:
        """
        Synthesize the final response for the user based on the AgentState.

        Args:
            agent_state (AgentState): The complete state of the agent.

        Returns:
            str: The synthesized response.
        """
        try:
            logger.info("Starting synthesis process.")

            # Step 1: Read execution history
            task_summaries = self._read_task_summaries(agent_state)
            retrieved_chunks = agent_state.retrieved_context

            # Validate retrieved chunks
            if not all(isinstance(chunk, RetrievedChunk) for chunk in retrieved_chunks):
                logger.error("Invalid retrieved chunks in AgentState.")
                raise ValueError("AgentState contains invalid retrieved chunks.")

            # Get current task
            task = next((t for t in agent_state.tasks if t.task_id == agent_state.current_task_id), None)
            if not task and agent_state.tasks:
                task = agent_state.tasks[0]
            target_domain = task.target_domain if task else agent_state.target_domain

            # Filter chunks by domain
            retrieved_chunks = self._filter_chunks_by_domain(retrieved_chunks, target_domain)

            # Handle edge cases
            if not retrieved_chunks:
                logger.warning("No retrieved chunks available for synthesis.")
                return "No relevant information was found."

            # Incorporate verification feedback
            verification_feedback = agent_state.verification_feedback
            if verification_feedback:
                logger.info("Incorporating verification feedback into the response.")

            # Generate response
            response = "Here is the information you requested:\n"
            for chunk in retrieved_chunks:
                response += f"- {chunk.text} [{chunk.chunk_id}]\n"

            return response

        except Exception as e:
            logger.error("Synthesis process failed: %s", str(e))
            raise

    def _read_task_summaries(self, agent_state: AgentState) -> List[str]:
        """
        Read task summaries from the AgentState.

        Args:
            agent_state (AgentState): The complete state of the agent.

        Returns:
            List[str]: A list of task summaries.
        """
        return [task.description for task in agent_state.tasks]

    def _filter_chunks_by_domain(self, retrieved_chunks: List[RetrievedChunk], target_domain: str) -> List[RetrievedChunk]:
        """
        Filter retrieved chunks by the target domain.

        Args:
            retrieved_chunks (List[RetrievedChunk]): The retrieved chunks.
            target_domain (str): The target domain to filter chunks.

        Returns:
            List[RetrievedChunk]: The filtered chunks.
        """
        return [chunk for chunk in retrieved_chunks if chunk.metadata.get("domain") == target_domain]

# --- Node Wrapper ---
_synthesis_agent_instance = None

def synthesis_node(state: AgentState) -> dict:
    global _synthesis_agent_instance
    if _synthesis_agent_instance is None:
        _synthesis_agent_instance = SynthesisAgent()
        
    answer = _synthesis_agent_instance.synthesize(state)
    return {
        "answer": answer,
        "next_agent": "END"
    }

