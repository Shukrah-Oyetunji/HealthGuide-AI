
import os
from pathlib import Path

from pypdf import PdfReader


# ---------------------------------------------------------
# PATH CONFIGURATION
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DOCUMENTS_DIR = BASE_DIR / "documents"
CHROMA_DIR = BASE_DIR / "rag" / "chroma_db"

DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

ENABLE_LOCAL_RETRIEVAL = (
    os.getenv("ENABLE_LOCAL_RETRIEVAL", "true").lower() == "true"
)


# ---------------------------------------------------------
# LAZY CHROMADB INITIALIZATION
# ---------------------------------------------------------

_client = None
_collection = None


def get_collection():
    """Initialize ChromaDB only when local retrieval is needed."""

    global _client, _collection

    if _collection is None:
        import chromadb

        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR)
        )

        _collection = _client.get_or_create_collection(
            name="health_documents",
            metadata={"hnsw:space": "cosine"},
        )

    return _collection


# ---------------------------------------------------------
# LAZY EMBEDDING MODEL INITIALIZATION
# ---------------------------------------------------------

_embedding_model = None


def get_embedding_model():
    """Load the embedding model only when required."""

    global _embedding_model

    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

    return _embedding_model


# ---------------------------------------------------------
# PDF EXTRACTION
# ---------------------------------------------------------

def extract_pdf_pages(pdf_path: Path) -> list[dict]:
    """Extract PDF text while preserving page numbers."""

    reader = PdfReader(str(pdf_path))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        if text.strip():
            pages.append({
                "page": page_number,
                "text": text.strip(),
            })

    return pages


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract all PDF text with page markers."""

    pages = extract_pdf_pages(pdf_path)

    return "\n\n".join(
        f"[Page {page['page']}]\n{page['text']}"
        for page in pages
    )


# ---------------------------------------------------------
# TEXT CHUNKING
# ---------------------------------------------------------

def split_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[str]:
    """Split text into overlapping character-based chunks."""

    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Use chunk_size > overlap >= 0.")

    text = " ".join(text.split())
    chunks = []

    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


# ---------------------------------------------------------
# PDF INDEXING
# ---------------------------------------------------------

def index_pdf(pdf_path: Path) -> int:
    """Extract, split, embed, and index a single PDF."""

    if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Provide a valid PDF file.")

    pages = extract_pdf_pages(pdf_path)

    if not pages:
        raise ValueError(
            f"No extractable text in {pdf_path.name}. "
            "The PDF may be scanned and require OCR."
        )

    chunks = []
    metadatas = []

    for page in pages:
        page_chunks = split_text(page["text"])

        for chunk in page_chunks:
            chunks.append(chunk)

            metadatas.append({
                "source": pdf_path.name,
                "page": page["page"],
                "chunk": len(chunks),
            })

    if not chunks:
        raise ValueError("No text chunks were generated.")

    ids = [
        f"{pdf_path.stem}-{i}"
        for i in range(len(chunks))
    ]

    collection = get_collection()

    # Replace previous chunks from the same PDF.
    collection.delete(
        where={"source": pdf_path.name}
    )

    embeddings = get_embedding_model().encode(
        chunks,
        normalize_embeddings=True,
    ).tolist()

    collection.upsert(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    return len(chunks)


def index_all_pdfs() -> dict[str, int]:
    """Index all PDFs inside the documents folder."""

    results = {}

    for pdf_path in sorted(DOCUMENTS_DIR.glob("*.pdf")):
        results[pdf_path.name] = index_pdf(pdf_path)

    return results


# ---------------------------------------------------------
# LOCAL DOCUMENT RETRIEVAL
# ---------------------------------------------------------

def search_health_documents(
    question: str,
    top_k: int = 3,
) -> list[dict]:
    """Retrieve relevant passages from indexed local documents."""

    if not question.strip():
        raise ValueError("Question cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    # Skip local retrieval entirely when disabled.
    if not ENABLE_LOCAL_RETRIEVAL:
        return []

    collection = get_collection()

    document_count = collection.count()

    if document_count == 0:
        return []

    query_embedding = get_embedding_model().encode(
        [question],
        normalize_embeddings=True,
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, document_count),
        include=["documents", "metadatas", "distances"],
    )

    passages = []

    for i, document in enumerate(results["documents"][0]):
        metadata = results["metadatas"][0][i]
        distance = results["distances"][0][i]

        passages.append({
            "text": document,
            "source": metadata["source"],
            "page": metadata.get("page"),
            "chunk": metadata["chunk"],
            "distance": distance,
        })

    return passages
