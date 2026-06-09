from pathlib import Path
from typing import List
import uuid
from pypdf import PdfReader
from qdrant_client.models import PointStruct
from backend.rag.embeddings import EmbeddingModel
from backend.rag.qdrant_store import get_client
from backend.config import settings


def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i: i + chunk_size]))
        i += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 30]


def ingest_pdf(pdf_path: Path, tag: str = "general") -> int:
    reader = PdfReader(str(pdf_path))
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return _ingest_text(full_text, source=pdf_path.name, tag=tag)


def ingest_text_file(txt_path: Path, tag: str = "general") -> int:
    text = txt_path.read_text(encoding="utf-8", errors="ignore")
    return _ingest_text(text, source=txt_path.name, tag=tag)


def _ingest_text(text: str, source: str, tag: str) -> int:
    chunks = _chunk_text(text)
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
    for pdf in dir_path.glob("*.pdf"):
        n = ingest_pdf(pdf, tag=tag)
        print(f"Ingested {n} chunks from {pdf.name}")
        total += n
    for txt in dir_path.glob("*.txt"):
        n = ingest_text_file(txt, tag=tag)
        print(f"Ingested {n} chunks from {txt.name}")
        total += n
    return total


if __name__ == "__main__":
    from pathlib import Path
    base = Path(__file__).parent.parent.parent / "rag_data"

    from backend.rag.qdrant_store import init_collection
    init_collection()

    total = 0
    for folder, tag in [("crop_guides", "crop_guide"), ("pest_control", "pest_control")]:
        path = base / folder
        if path.exists():
            n = ingest_directory(path, tag=tag)
            total += n
        else:
            print(f"Skipping {folder}/ — folder not found")

    print(f"\nDone. Total chunks ingested: {total}")
    print("Advisory page is now ready to answer crop questions.")
