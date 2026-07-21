from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
from src.retrieval.dense_search import DenseSearch
from src.retrieval.sparse_search import SparseSearch
from src.retrieval.fusion import ReciprocalRankFusion
from src.retrieval.dense_search import SearchResult
from src.agents.state import RetrievedChunk, AgentState, Task
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RetrievalAgent:
    """
    The Retrieval Agent handles the retrieval process for a given task, including dense and sparse retrieval,
    reciprocal rank fusion, metadata filtering, and context preparation for downstream agents.
    """

    dense_search: DenseSearch
    sparse_search: SparseSearch
    rrf: ReciprocalRankFusion
    embedding_model: SentenceTransformer

    def __init__(self, dense_search: DenseSearch, sparse_search: SparseSearch, rrf: ReciprocalRankFusion):
        """
        Initialize the RetrievalAgent with dense and sparse search modules, RRF, and the embedding model.

        Args:
            dense_search (DenseSearch): The dense retrieval module.
            sparse_search (SparseSearch): The sparse retrieval module.
            rrf (ReciprocalRankFusion): The reciprocal rank fusion module.
        """
        self.dense_search = dense_search
        self.sparse_search = sparse_search
        self.rrf = rrf
        self.embedding_model = SentenceTransformer("intfloat/multilingual-e5-base")
        logger.info("RetrievalAgent initialized with mE5 embedding model.")

    def execute(self, agent_state: AgentState) -> AgentState:
        """
        Execute the retrieval task based on the current AgentState.

        Args:
            agent_state (AgentState): The current state of the agent.

        Returns:
            AgentState: The updated state of the agent after retrieval.
        """
        try:
            logger.info("Starting retrieval task execution.")

            # Step 1: Get the current task
            task = next((t for t in agent_state.tasks if t.task_id == agent_state.current_task_id), None)
            if not task and agent_state.tasks:
                task = agent_state.tasks[0]
            if not task:
                logger.warning("No active task found in AgentState.")
                return self._update_status(agent_state, "NO_TASK")

            logger.info("Processing task: %s", task.task_id)

            # Step 2: Extract task details
            task_description = task.description
            target_domain = task.target_domain
            task_id = getattr(task, 'task_id', 'unknown')

            # Step 3: Check execution history
            if self._should_skip_task(agent_state, task):
                logger.info("Task %s skipped due to unmet conditions.", task_id)
                return self._update_status(agent_state, "CONDITION_NOT_MET")

            # Step 4: Generate optimized query
            optimized_query = self._generate_query(task_description)

            # Step 5: Encode query using mE5
            encoded_query = self._encode_query(optimized_query)

            # Step 6: Run Dense Search
            top_k = getattr(task, 'top_k', 5)
            dense_results = self.dense_search.search(
                query=optimized_query, domain=target_domain, metadata=getattr(task, 'metadata', {}), top_k=top_k
            )
            logger.info("Dense search completed with %d results.", len(dense_results))

            # Step 7: Run Sparse Search
            sparse_results = self.sparse_search.search(query=optimized_query, top_k=top_k)
            logger.info("Sparse search completed with %d results.", len(sparse_results))

            # Step 8: Fuse results using RRF
            fused_results = self.rrf.fuse(dense_results, sparse_results)
            logger.info("Reciprocal Rank Fusion completed with %d fused results.", len(fused_results))

            # Step 9: Filter results by domain
            filtered_results = self._filter_results_by_domain(fused_results, target_domain)
            logger.info("Filtered results to %d based on domain: %s.", len(filtered_results), target_domain)

            # Step 10: Return Top K results
            top_results = filtered_results[:top_k]

            # Step 11: Convert to RetrievedChunk objects
            retrieved_chunks = self._convert_to_retrieved_chunks(top_results)

            # Step 12: Update AgentState
            agent_state = self._update_agent_state(agent_state, retrieved_chunks, task, "SUCCESS")

            # Step 13: Handle edge cases
            if not retrieved_chunks:
                logger.warning("No records retrieved for task %s.", task_id)
                return self._update_status(agent_state, "NO_RECORDS")

            context_window = getattr(task, 'context_window', 4000)
            if len(retrieved_chunks) > context_window:
                logger.info("Results exceed context window. Generating smart summary.")
                agent_state = self._generate_smart_summary(agent_state, retrieved_chunks, task)

            # Step 15: Set next agent
            agent_state.next_agent = "Verification_Agent"
            logger.info("Next agent set to Verification_Agent.")

            return agent_state

        except Exception as e:
            logger.error("Retrieval task execution failed: %s", str(e))
            return self._update_status(agent_state, "ERROR")

    def _should_skip_task(self, agent_state: AgentState, task: Task) -> bool:
        """
        Check if the task should be skipped based on execution history.

        Args:
            agent_state (AgentState): The current state of the agent.
            task (Task): The current task.

        Returns:
            bool: True if the task should be skipped, False otherwise.
        """
        # Example condition: Check if the task has already been completed
        return task.status == "completed"

    def _generate_query(self, task_description: str) -> str:
        """
        Generate an optimized query from the task description.

        Args:
            task_description (str): The task description.

        Returns:
            str: The optimized query.
        """
        return f"query: {task_description}"

    def _encode_query(self, query: str) -> List[float]:
        """
        Encode the query using the mE5 embedding model.

        Args:
            query (str): The query to encode.

        Returns:
            List[float]: The encoded query vector.
        """
        return self.embedding_model.encode(query, normalize_embeddings=True)

    def _filter_results_by_domain(self, results: List[SearchResult], domain: str) -> List[SearchResult]:
        """
        Filter results by the specified domain.

        Args:
            results (List[SearchResult]): The search results.
            domain (str): The target domain.

        Returns:
            List[SearchResult]: The filtered results.
        """
        return [result for result in results if result.payload.get("domain") == domain]

    def _convert_to_retrieved_chunks(self, results: List[SearchResult]) -> List[RetrievedChunk]:
        """
        Convert SearchResult objects to RetrievedChunk objects.

        Args:
            results (List[SearchResult]): The search results.

        Returns:
            List[RetrievedChunk]: The retrieved chunks.
        """
        return [
            RetrievedChunk(
                chunk_id=result.payload.get("chunk_id"),
                file_name=result.payload.get("document_name"),
                text=result.payload.get("text"),
                metadata=result.payload.get("metadata", {}),
                score=result.score,
            )
            for result in results
        ]

    def _update_agent_state(self, agent_state: AgentState, chunks: List[RetrievedChunk], task: Task, status: str) -> AgentState:
        """
        Update the AgentState with the retrieved chunks and task status.

        Args:
            agent_state (AgentState): The current state of the agent.
            chunks (List[RetrievedChunk]): The retrieved chunks.
            task (Task): The current task.
            status (str): The task status.

        Returns:
            AgentState: The updated agent state.
        """
        agent_state.retrieved_context = chunks
        if task:
            task.status = status
        return agent_state

    def _update_status(self, agent_state: AgentState, status: str) -> AgentState:
        """
        Update the status of the AgentState.

        Args:
            agent_state (AgentState): The current state of the agent.
            status (str): The new status.

        Returns:
            AgentState: The updated agent state.
        """
        task = next((t for t in agent_state.tasks if t.task_id == agent_state.current_task_id), None)
        if task:
            task.status = status
        return agent_state

    def _generate_smart_summary(self, agent_state: AgentState, chunks: List[RetrievedChunk], task: Task) -> AgentState:
        """
        Generate a smart summary for large context windows.

        Args:
            agent_state (AgentState): The current state of the agent.
            chunks (List[RetrievedChunk]): The retrieved chunks.

        Returns:
            AgentState: The updated agent state with the summary.
        """
        try:
            logger.info("Generating smart summary for %d chunks.", len(chunks))

            if not chunks:
                logger.warning("No chunks provided for summarization.")
                if task:
                    task.result_summary = "No content available for summarization."
                return agent_state

            # Combine text from chunks into a single summary
            combined_text = " ".join(chunk.text for chunk in chunks)

            # Check if the combined text exceeds the context window
            context_window = getattr(task, 'context_window', 4000)
            if len(combined_text) > context_window:
                logger.info("Combined text exceeds context window. Summarizing content.")
                # Example summarization logic (replace with actual summarization model if available)
                summary = self._summarize_text(combined_text)
            else:
                summary = combined_text

            # Add citations for each chunk
            citations = [
                f"[{getattr(chunk, 'file_name', 'Unknown Document')} - {chunk.chunk_id}]"
                for chunk in chunks
            ]
            summary_with_citations = f"{summary}\n\nCitations:\n" + "\n".join(citations)

            # Update the agent state with the summary
            if task:
                task.result_summary = summary_with_citations
            logger.info("Smart summary generated successfully.")
            return agent_state

        except Exception as e:
            logger.error("Failed to generate smart summary: %s", str(e))
            raise

    def _summarize_text(self, text: str) -> str:
        """
        Summarize the given text. This is a placeholder for an actual summarization model.

        Args:
            text (str): The text to summarize.

        Returns:
            str: The summarized text.
        """
        # Placeholder logic: Return the first 500 characters as a summary
        return text[:500] + "..."

# --- Node Wrapper ---
_retrieval_agent_instance = None

def retrieval_node(state: AgentState) -> dict:
    global _retrieval_agent_instance
    if _retrieval_agent_instance is None:
        dense = DenseSearch(qdrant_url="http://localhost:6333", collection_name="my_collection")
        sparse = SparseSearch()
        rrf = ReciprocalRankFusion()
        _retrieval_agent_instance = RetrievalAgent(dense_search=dense, sparse_search=sparse, rrf=rrf)
        
    updated_state = _retrieval_agent_instance.execute(state)
    
    return {
        "retrieved_context": updated_state.retrieved_context,
        "tasks": updated_state.tasks,
        "next_agent": updated_state.next_agent,
    }
