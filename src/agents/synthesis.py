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
            verification_feedback = agent_state.verification_feedback

            # Step 2: Handle scenarios
            if agent_state.status == "CONDITION_NOT_MET":
                logger.info("Task was skipped due to unmet conditions.")
                return self._handle_conditional_skip(verification_feedback)

            if agent_state.status == "ACCESS_DENIED":
                logger.info("Access denied due to RBAC restrictions.")
                return self._handle_access_denied()

            if agent_state.status == "NO_RECORDS":
                logger.info("No records found for the task.")
                return self._handle_no_records()

            if agent_state.status == "CASUAL_CONVERSATION":
                logger.info("Handling casual conversation scenario.")
                return self._handle_casual_conversation(agent_state)

            if agent_state.status == "MIXED_RESULTS":
                logger.info("Handling mixed results scenario.")
                return self._handle_mixed_results(task_summaries, retrieved_chunks)

            # Step 3: Normal Retrieval
            logger.info("Handling normal retrieval scenario.")
            return self._handle_normal_retrieval(retrieved_chunks)

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

    def _handle_conditional_skip(self, feedback: str) -> str:
        """
        Handle the conditional skip scenario.

        Args:
            feedback (str): The feedback explaining why the task was skipped.

        Returns:
            str: The response for the conditional skip scenario.
        """
        return f"The task was skipped: {feedback}"

    def _handle_access_denied(self) -> str:
        """
        Handle the access denied scenario.

        Returns:
            str: The response for the access denied scenario.
        """
        return "Access to the requested information is restricted due to RBAC policies."

    def _handle_no_records(self) -> str:
        """
        Handle the no records scenario.

        Returns:
            str: The response for the no records scenario.
        """
        return "No relevant information was found for the requested task."

    def _handle_casual_conversation(self, agent_state: AgentState) -> str:
        """
        Handle the casual conversation scenario.

        Args:
            agent_state (AgentState): The complete state of the agent.

        Returns:
            str: The response for the casual conversation scenario.
        """
        return "This is a casual conversation. How can I assist you further?"

    def _handle_mixed_results(self, task_summaries: List[str], retrieved_chunks: List[RetrievedChunk]) -> str:
        """
        Handle the mixed results scenario.

        Args:
            task_summaries (List[str]): The summaries of the tasks.
            retrieved_chunks (List[RetrievedChunk]): The retrieved chunks.

        Returns:
            str: The response for the mixed results scenario.
        """
        response = "The results for your request are as follows:\n"
        for chunk in retrieved_chunks:
            response += f"- {chunk.text} [{chunk.chunk_id}]\n"
        return response

    def _handle_normal_retrieval(self, retrieved_chunks: List[RetrievedChunk]) -> str:
        """
        Handle the normal retrieval scenario.

        Args:
            retrieved_chunks (List[RetrievedChunk]): The retrieved chunks.

        Returns:
            str: The response for the normal retrieval scenario.
        """
        if not retrieved_chunks:
            logger.warning("No retrieved chunks available for normal retrieval.")
            return "No relevant information was found."

        response = "Here is the information you requested:\n"
        for chunk in retrieved_chunks:
            response += f"- {chunk.text} [{chunk.chunk_id}]\n"
        return response


# Example AgentState
agent_state = AgentState(
    status="NORMAL_RETRIEVAL",
    retrieved_context=[
        RetrievedChunk(chunk_id="1", document_name="doc1", text="This is the first chunk.", metadata={}, score=0.9),
        RetrievedChunk(chunk_id="2", document_name="doc2", text="This is the second chunk.", metadata={}, score=0.8),
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