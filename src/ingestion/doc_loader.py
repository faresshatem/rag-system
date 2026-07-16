from pathlib import Path

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)


class DocumentLoader:
    """Load supported documents into LangChain Document objects."""

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".txt",
        ".docx",
    }

    @staticmethod
    def load(file_path: str) -> list[Document]:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"{file_path} is not a file.")

        extension = path.suffix.lower()

        if extension not in DocumentLoader.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {extension}. "
                f"Supported: {DocumentLoader.SUPPORTED_EXTENSIONS}"
            )

        if extension == ".pdf":
            loader = PyPDFLoader(str(path))

        elif extension == ".docx":
            loader = Docx2txtLoader(str(path))

        else:
            loader = TextLoader(str(path), encoding="utf-8")

        documents = loader.load()

        if not documents:
            raise ValueError("No content could be extracted from the document.")

        return documents