"""
Hybrid retriever — fuses dense (Qdrant ANN) + sparse (BM25) results via
Reciprocal Rank Fusion (RRF), then applies MMR for diversity.

RRF score = 1/(k + rank_dense) + 1/(k + rank_bm25)   where k = 60

Usage:
    results = await retrieve_hybrid(query, top_k=5)
    # returns list of {text, source, tag, score, retrieval_method}
"""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

RRF_K = 60   # standard RRF constant — higher = less steep rank dropoff


async def retrieve_hybrid(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.20,
    alpha: float = 0.5,     # weight balance: 0 = pure BM25, 1 = pure dense
) -> list[dict[str, Any]]:
    """
    Hybrid retrieval: dense + BM25 → RRF fusion → MMR.

    alpha=0.5 weights both sources equally.
    Returns up to top_k results with a merged `score` field.
    """
    dense_results, bm25_results = await asyncio.gather(
        _dense_search(query, k=top_k * 3, threshold=score_threshold),
        asyncio.to_thread(_bm25_search, query, k=top_k * 3),
    )

    fused = _rrf_fuse(dense_results, bm25_results, alpha=alpha)

    # Apply MMR for diversity over fused pool
    from backend.rag.mmr import mmr_select
    from backend.rag.embeddings import EmbeddingModel

    if fused:
        embedder = EmbeddingModel.get_instance()
        try:
            for doc in fused:
                if "vector" not in doc:
                    doc["vector"] = await asyncio.to_thread(embedder.embed_one, doc["text"])
        except Exception:
            pass
        selected = mmr_select(fused, top_k=top_k, lambda_mult=0.6)
    else:
        selected = []

    return selected


def _rrf_fuse(
    dense: list[dict[str, Any]],
    bm25: list[dict[str, Any]],
    alpha: float = 0.5,
) -> list[dict[str, Any]]:
    """
    Reciprocal Rank Fusion.
    dense items carry "score" (cosine), bm25 items carry "bm25_score".
    Returns merged list with unified "score" field, de-duped by text.
    """
    scores: dict[str, float] = {}
    texts: dict[str, dict[str, Any]] = {}

    for rank, doc in enumerate(dense):
        key = doc["text"]
        scores[key] = scores.get(key, 0.0) + alpha * (1.0 / (RRF_K + rank))
        texts[key] = dict(doc)
        texts[key]["retrieval_method"] = "dense"

    for rank, doc in enumerate(bm25):
        key = doc["text"]
        scores[key] = scores.get(key, 0.0) + (1 - alpha) * (1.0 / (RRF_K + rank))
        if key not in texts:
            texts[key] = dict(doc)
            texts[key]["retrieval_method"] = "bm25"
        else:
            texts[key]["retrieval_method"] = "hybrid"

    merged = []
    for text_key, doc in texts.items():
        doc["score"] = round(scores[text_key], 6)
        merged.append(doc)

    merged.sort(key=lambda d: d["score"], reverse=True)
    return merged


async def _dense_search(query: str, k: int, threshold: float) -> list[dict[str, Any]]:
    """Dense ANN search via Qdrant — reuses existing retriever logic."""
    try:
        from backend.rag.retriever import _vector_search
        from backend.rag.embeddings import EmbeddingModel
        embedder = EmbeddingModel.get_instance()
        vector = await asyncio.to_thread(embedder.embed_one, query)
        results = await asyncio.to_thread(_vector_search, vector, k, threshold)
        return results
    except Exception as e:
        logger.warning("Dense search failed: %s", e)
        return []


def _bm25_search(query: str, k: int) -> list[dict[str, Any]]:
    """BM25 search — blocking, call via to_thread."""
    try:
        from backend.rag.bm25_retriever import get_index
        return get_index().search(query, k=k)
    except Exception as e:
        logger.warning("BM25 search failed: %s", e)
        return []
