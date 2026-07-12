from typing import List, Dict, Any
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RankedResult:
    id: str
    score: float
    metadata: Dict[str, Any]

def reciprocal_rank_fusion(
    dense_results: List[RankedResult],
    sparse_results: List[RankedResult],
    k: int = 60
) -> List[RankedResult]:
    """
    Perform Reciprocal Rank Fusion (RRF) to merge dense and sparse rankings.

    Args:
        dense_results (List[RankedResult]): Ranked results from dense retrieval.
        sparse_results (List[RankedResult]): Ranked results from sparse retrieval.
        k (int): The rank cutoff for RRF computation. Default is 60.

    Returns:
        List[RankedResult]: Unified ranked list sorted in descending order of RRF scores.
    """
    try:
        logger.info("Starting Reciprocal Rank Fusion (RRF).")
        
        # Combine dense and sparse results into a single dictionary
        combined_scores = {}
        for rank, result in enumerate(dense_results):
            weight = 1 / (rank + 1 + k)
            if result.id not in combined_scores:
                combined_scores[result.id] = {"score": 0, "metadata": result.metadata}
            combined_scores[result.id]["score"] += weight
            logger.debug(f"Dense result {result.id} updated with weight {weight}.")

        for rank, result in enumerate(sparse_results):
            weight = 1 / (rank + 1 + k)
            if result.id not in combined_scores:
                combined_scores[result.id] = {"score": 0, "metadata": result.metadata}
            combined_scores[result.id]["score"] += weight
            logger.debug(f"Sparse result {result.id} updated with weight {weight}.")

        # Create a unified ranked list
        unified_results = [
            RankedResult(id=doc_id, score=data["score"], metadata=data["metadata"])
            for doc_id, data in combined_scores.items()
        ]

        # Sort the results in descending order of scores
        unified_results.sort(key=lambda x: x.score, reverse=True)
        logger.info("RRF computation completed successfully.")

        return unified_results

    except Exception as e:
        logger.error(f"An error occurred during RRF computation: {e}")
        raise