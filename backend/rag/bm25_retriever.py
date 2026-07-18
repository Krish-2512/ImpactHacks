"""
BM25 sparse retriever — keyword-based retrieval over the knowledge base.

The BM25Index is built lazily from all Qdrant payload texts on first call,
then cached in memory. Rebuilt after ingestion via `reset()`.

rank-bm25 is already installed (rank-bm25>=0.2.2 in requirements.txt).
"""
from __future__ import annotations
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

_INDEX: "BM25Index | None" = None


def get_index() -> "BM25Index":
    global _INDEX
    if _INDEX is None:
        _INDEX = BM25Index()
        _INDEX.build()
    return _INDEX


def reset() -> None:
    """Call after ingesting new documents to force a rebuild."""
    global _INDEX
    _INDEX = None


class BM25Index:
    """Lazy BM25 index built from all documents in the Qdrant collection."""

    def __init__(self) -> None:
        self._bm25 = None
        self._docs: list[dict[str, Any]] = []
        self._tokenized: list[list[str]] = []

    def build(self) -> None:
        """Scroll Qdrant for all payloads and build the BM25 index."""
        try:
            from rank_bm25 import BM25Okapi
            from backend.rag.qdrant_store import get_client
            from backend.config import settings

            client = get_client()
            docs = []
            offset = None

            while True:
                batch, offset = client.scroll(
                    collection_name=settings.QDRANT_COLLECTION,
                    limit=200,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                for point in batch:
                    payload = point.payload or {}
                    text = payload.get("text", "")
                    if text:
                        docs.append({
                            "text":   text,
                            "source": payload.get("source", ""),
                            "tag":    payload.get("tag", ""),
                        })
                if offset is None:
                    break

            if not docs:
                logger.warning("BM25: no documents found in collection")
                return

            self._docs = docs
            self._tokenized = [_tokenize(d["text"]) for d in docs]
            self._bm25 = BM25Okapi(self._tokenized)
            logger.info("BM25 index built: %d documents", len(docs))

        except Exception as e:
            logger.error("BM25 index build failed: %s", e)

    def search(self, query: str, k: int = 10) -> list[dict[str, Any]]:
        """Return top-k BM25 results as list of {text, source, tag, bm25_score}."""
        if self._bm25 is None:
            return []
        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]
        results = []
        for idx, score in ranked:
            if score <= 0:
                continue
            doc = dict(self._docs[idx])
            doc["bm25_score"] = float(score)
            results.append(doc)
        return results


def _tokenize(text: str) -> list[str]:
    """Lowercase + remove punctuation + split."""
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()
