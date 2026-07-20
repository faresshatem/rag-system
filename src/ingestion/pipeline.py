import uuid

from .doc_loader import DocumentLoader
from .chunker import DocumentChunker
from .embedding import EmbeddingGenerator
from .db_connector import QdrantConnector


def ingest_document(
    *,
    file_path: str,
    domain: str,
    file_name: str,
) -> None:
    """
    Execute the complete document ingestion pipeline.

    """

    document_id = str(uuid.uuid4())

    loader = DocumentLoader()
    documents = loader.load(file_path)

    chunker = DocumentChunker()
    chunks = chunker.chunk(
        documents,
        document_id=document_id,
        domain=domain,
        file_name=file_name,
    )

    embedding = EmbeddingGenerator()
    vectors = embedding.embed_documents(chunks)

    if not vectors:
        return

    qdrant = QdrantConnector()

    qdrant.create_collection(
        vector_size=len(vectors[0]),
    )

    qdrant.upload_documents(
        vectors,
        chunks,
    )