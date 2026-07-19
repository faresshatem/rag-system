from typing import List, Dict, Any
from dataclasses import dataclass
from src.models import AgentState, RetrievedChunk, Task
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

            # Filter chunks by domain
            retrieved_chunks = self._filter_chunks_by_domain(retrieved_chunks, agent_state.current_task.target_domain)

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


# Example AgentState
agent_state = AgentState(
    status="NORMAL_RETRIEVAL",
    retrieved_context=[
        RetrievedChunk(chunk_id="1", document_name="doc1", text="This is the first chunk.", metadata={"domain": "HR"}, score=0.9),
        RetrievedChunk(chunk_id="2", document_name="doc2", text="This is the second chunk.", metadata={"domain": "Finance"}, score=0.8),
    ],
    tasks=[
        Task(id="task1", description="Retrieve HR policies", target_domain="HR"),
    ],
    verification_feedback="Valid context.",
)

# Initialize SynthesisAgent
synthesis_agent = SynthesisAgent()

# Generate response
response = synthesis_agent.synthesize(agent_state)

# Print the response
print(response)