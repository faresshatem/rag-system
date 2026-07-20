from typing import List, Dict, Any
from dataclasses import dataclass
from src.models import AgentState, Task, RetrievedChunk
from src.llm import LLM  # Assuming the project's LLM interface is implemented in src.llm
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VerificationAgent:
    """
    The Verification Agent evaluates whether the retrieved context satisfies the current task.
    """

    llm: LLM

    def verify(self, agent_state: AgentState) -> AgentState:
        """
        Verify the retrieved context for the current task.

        Args:
            agent_state (AgentState): The current state of the agent.

        Returns:
            AgentState: The updated state of the agent after verification.
        """
        try:
            logger.info("Starting verification process.")

            # Step 1: Locate the active task
            task = agent_state.current_task
            if not task:
                logger.warning("No active task found in AgentState.")
                return self._update_agent_state(agent_state, True, "Skipped", "Supervisor")

            logger.info("Verifying task: %s", task.id)

            # Step 2: Read retrieved chunks
            retrieved_chunks = agent_state.retrieved_context

            # Step 3: Fast Rule Evaluation
            if agent_state.status in ["CONDITION_NOT_MET", "SKIPPED"]:
                logger.info("Task skipped or condition not met. Marking context as valid.")
                return self._update_agent_state(agent_state, True, "Skipped", "Supervisor")

            if not retrieved_chunks:
                logger.warning("No records found for task: %s", task.id)
                return self._update_agent_state(agent_state, False, "No data found", "Supervisor")

            # Step 4: Use LLM to evaluate the task description and retrieved context
            task_description = task.description
            context_text = self._combine_chunks(retrieved_chunks)

            logger.info("Sending task description and context to LLM for evaluation.")
            llm_response = self.llm.evaluate(task_description=task_description, context=context_text)

            is_valid = llm_response.get("is_valid", False)
            feedback = llm_response.get("feedback", "No feedback provided.")

            # Step 5: Update AgentState based on LLM response
            if is_valid:
                logger.info("LLM verified the context as valid.")
                return self._update_agent_state(agent_state, True, "Valid context", "Supervisor")
            else:
                logger.info("LLM determined the context is invalid. Feedback: %s", feedback)
                return self._update_agent_state(agent_state, False, feedback, "Supervisor")

        except Exception as e:
            logger.error("Verification process failed: %s", str(e))
            raise

    def _combine_chunks(self, chunks: List[RetrievedChunk]) -> str:
        """
        Combine the text of retrieved chunks into a single context string.

        Args:
            chunks (List[RetrievedChunk]): The retrieved chunks.

        Returns:
            str: The combined context text.
        """
        return " ".join(chunk.text for chunk in chunks)

    def _update_agent_state(
        self, agent_state: AgentState, is_context_valid: bool, feedback: str, next_agent: str
    ) -> AgentState:
        """
        Update the AgentState with verification results.

        Args:
            agent_state (AgentState): The current state of the agent.
            is_context_valid (bool): Whether the context is valid.
            feedback (str): Feedback from the verification process.
            next_agent (str): The next agent to execute.

        Returns:
            AgentState: The updated agent state.
        """
        agent_state.is_context_valid = is_context_valid
        agent_state.verification_feedback = feedback
        agent_state.next_agent = next_agent
        return agent_state


# Example LLM implementation
class MockLLM:
    def evaluate(self, task_description: str, context: str) -> Dict[str, Any]:
        # Mock evaluation logic
        if "valid" in context:
            return {"is_valid": True, "feedback": "Context is valid."}
        else:
            return {"is_valid": False, "feedback": "Context is invalid. Please refine your query."}

# Example AgentState
agent_state = AgentState(
    current_task=Task(id="task1", description="Verify HR policies", target_domain="HR"),
    retrieved_context=[
        RetrievedChunk(chunk_id="1", document_name="doc1", text="This is a valid HR policy.", metadata={}, score=0.9),
        RetrievedChunk(chunk_id="2", document_name="doc2", text="Another valid HR policy.", metadata={}, score=0.8),
    ],
    status="",
    is_context_valid=False,
    verification_feedback="",
    next_agent="",
)

if not agent_state or not agent_state.current_task:
    logger.error("Invalid AgentState: Missing current task.")
else:
    # Initialize VerificationAgent
    logger.info("Initializing VerificationAgent with MockLLM.")
    verification_agent = VerificationAgent(llm=MockLLM())

    # Perform verification
    logger.info("Starting verification process.")
    updated_state = verification_agent.verify(agent_state)

    # Log and print updated AgentState
    logger.info("Verification completed. Updated AgentState: %s", updated_state)
    print(updated_state)