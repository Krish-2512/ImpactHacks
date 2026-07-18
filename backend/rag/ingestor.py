"""
RAG ingestor with semantic chunking via RecursiveCharacterTextSplitter.
Splits on paragraph → sentence → word boundaries for better context preservation
compared to the old fixed word-count approach.
"""
import uuid
from pathlib import Path
from typing import List

from pypdf import PdfReader
from qdrant_client.models import PointStruct
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.rag.embeddings import EmbeddingModel
from backend.rag.qdrant_store import get_client
from backend.config import settings


_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,       # characters — finer-grained than old 400 words
    chunk_overlap=120,
    separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
    length_function=len,
)


def _extract_text_from_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def ingest_pdf(pdf_path: Path, tag: str = "general") -> int:
    text = _extract_text_from_pdf(pdf_path)
    return _ingest_text(text, source=pdf_path.name, tag=tag)


def ingest_text_file(txt_path: Path, tag: str = "general") -> int:
    text = txt_path.read_text(encoding="utf-8", errors="ignore")
    return _ingest_text(text, source=txt_path.name, tag=tag)


def _ingest_text(text: str, source: str, tag: str) -> int:
    chunks: List[str] = [
        c.strip() for c in _splitter.split_text(text) if len(c.strip()) > 40
    ]
    if not chunks:
        return 0

    embedder = EmbeddingModel.get_instance()
    vectors = embedder.embed(chunks)

    client = get_client()
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={"text": chunk, "source": source, "tag": tag},
        )
        for chunk, vec in zip(chunks, vectors)
    ]
    client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)
    return len(points)


def ingest_directory(dir_path: Path, tag: str = "crop_guide") -> int:
    total = 0
    for pdf in sorted(dir_path.glob("*.pdf")):
        n = ingest_pdf(pdf, tag=tag)
        print(f"  Ingested {n} chunks from {pdf.name}")
        total += n
    for txt in sorted(dir_path.glob("*.txt")):
        n = ingest_text_file(txt, tag=tag)
        print(f"  Ingested {n} chunks from {txt.name}")
        total += n
    return total


if __name__ == "__main__":
    base = Path(__file__).parent.parent.parent / "rag_data"

    from backend.rag.qdrant_store import init_collection
    init_collection()

    total = 0
    for folder, tag in [("crop_guides", "crop_guide"), ("pest_control", "pest_control")]:
        path = base / folder
        if path.exists():
            print(f"\nIngesting {folder}/...")
            n = ingest_directory(path, tag=tag)
            total += n
        else:
            print(f"Skipping {folder}/ — folder not found")

    print(f"\nDone. Total chunks ingested: {total}")
