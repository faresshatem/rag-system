from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

# Initialize Qdrant client
qdrant_client = QdrantClient("http://localhost:6333")  # Adjust the URL if needed

# Initialize the embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # You can use any SentenceTransformer model

def search_in_qdrant(query: str, target_domain: str, top_k: int):
    # Convert query to embedding
    query_embedding = embedding_model.encode(query).tolist()

    # Define metadata filter for the target domain
    metadata_filter = Filter(
        must=[
            FieldCondition(
                key="domain",
                match=MatchValue(value=target_domain)
            )
        ]
    )

    # Perform search in Qdrant
    search_results = qdrant_client.search(
        collection_name="your_collection_name",  # Replace with your Qdrant collection name
        query_vector=query_embedding,
        query_filter=metadata_filter,
        top=top_k
    )

    # Extract and return the top K chunks
    top_chunks = [result.payload for result in search_results]
    return top_chunks

# Example usage
if __name__ == "__main__":
    query = "What is the capital of France?"
    target_domain = "geography"
    top_k = 5

    results = search_in_qdrant(query, target_domain, top_k)
    print("Top K Results:", results)