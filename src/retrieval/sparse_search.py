from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from dataclasses import dataclass
from pydantic import BaseModel, Field
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Document:
    """
    Represents a document with text and metadata.
    """
    text: str
    metadata: Dict[str, Any]

class QueryResult(BaseModel):
    """
    Represents a query result with text, metadata, and score.
    """
    text: str = Field(..., description="The text content of the document.")
    metadata: Dict[str, Any] = Field(..., description="The metadata associated with the document.")
    score: float = Field(..., description="The BM25 score of the document.")

class SparseSearch:
    """
    A class to perform sparse retrieval using BM25.
    """

    def __init__(self) -> None:
        """
        Initializes the SparseSearch instance.
        """
        self.bm25 = None
        self.documents: List[Document] = []

    def tokenize_documents(self, documents: List[Document]) -> List[List[str]]:
        """
        Tokenizes the text of each document.

        Args:
            documents (List[Document]): A list of documents to tokenize.

        Returns:
            List[List[str]]: A list of tokenized documents.
        """
        logger.info("Tokenizing documents.")
        return [doc.text.split() for doc in documents]

    def build_index(self, documents: List[Document]) -> None:
        """
        Builds the BM25 index for the given documents.

        Args:
            documents (List[Document]): A list of documents to index.
        """
        logger.info("Building BM25 index.")
        self.documents = documents
        tokenized_corpus = self.tokenize_documents(documents)
        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int) -> List[QueryResult]:
        """
        Searches the indexed documents using the given query.

        Args:
            query (str): The search query.
            top_k (int): The number of top results to return.

        Returns:
            List[QueryResult]: A list of top_k ranked documents with scores.
        """
        if not self.bm25:
            logger.error("BM25 index is not built. Call build_index() first.")
            raise ValueError("BM25 index is not built. Call build_index() first.")

        logger.info("Scoring query against indexed documents.")
        tokenized_query = query.split()
        scores = self.bm25.get_scores(tokenized_query)
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        logger.info("Returning top_k ranked documents.")
        return [
            QueryResult(
                text=self.documents[i].text,
                metadata=self.documents[i].metadata,
                score=scores[i]
            )
            for i in ranked_indices
        ]

# Example usage:
# if __name__ == "__main__":
#     documents = [
#         Document(text="This is a test document.", metadata={"id": 1}),
#         Document(text="Another document for testing.", metadata={"id": 2}),
#     ]
#     search_engine = SparseSearch()
#     search_engine.build_index(documents)
#     results = search_engine.search(query="test", top_k=2)
#     for result in results:
#         print(result.json())