from typing import List, Dict, Any
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import ScoredPoint
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    id: str
    score: float
    payload: Dict[str, Any]

class DenseSearch:
    """
    A class to perform dense vector search using Qdrant and SentenceTransformer.
    """

    def __init__(self, qdrant_url: str = "http://localhost:6333", collection_name: str = None):
        """
        Initialize the DenseSearch instance.

        Args:
            qdrant_url (str): The URL of the Qdrant instance.
            collection_name (str): The name of the Qdrant collection to search.
        """
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION_NAME")
        if not self.collection_name:
            raise ValueError("Collection name must be provided or set in the environment variable 'QDRANT_COLLECTION_NAME'.")
        
        self.qdrant_client = QdrantClient(url=self.qdrant_url)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")  # Use a lightweight SentenceTransformer model

    def search_dense(self, query: str, target_domain: str, top_k: int = 5) -> List[SearchResult]:
        """
        Perform a dense vector search on the Qdrant collection.

        Args:
            query (str): The query string to search for.
            target_domain (str): The domain to filter results by.
            top_k (int): The number of top results to return.

        Returns:
            List[SearchResult]: A list of search results containing id, score, and payload.
        """
        try:
            # Generate query embedding
            logger.info("Generating embedding for the query.")
            query_embedding = self.model.encode(query).tolist()

            # Perform search in Qdrant
            logger.info("Performing search in Qdrant.")
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter={
                    "must": [
                        {
                            "key": "domain",
                            "match": {"value": target_domain}
                        }
                    ]
                },
                limit=top_k
            )

            # Process and return results
            logger.info("Processing search results.")
            return [
                SearchResult(
                    id=result.id,
                    score=result.score,
                    payload=result.payload
                )
                for result in search_results
            ]

        except Exception as e:
            logger.error(f"An error occurred during dense search: {e}")
            raise RuntimeError("Failed to perform dense search.") from e