"""
Hybrid RAG retriever:
- Multi-query expansion (3 variants via LLM)
- Hybrid retrieval: dense ANN (Qdrant) + sparse BM25 → RRF fusion
- MMR reranking for diversity
- Optional LLM context compression
- Returns full citation dicts {text, source, score, tag, retrieval_method}
"""
import asyncio
import logging
from backend.rag.qdrant_store import get_client
from backend.rag.mmr import mmr_select
from backend.config import settings

logger = logging.getLogger(__name__)


def _check_collection_has_data() -> bool:
    try:
        client = get_client()
        info = client.get_collection(settings.QDRANT_COLLECTION)
        return (info.points_count or 0) > 0
    except Exception:
        return False


def _vector_search(query_vector: list, top_k: int, score_threshold: float) -> list:
    """Single synchronous vector search — called via asyncio.to_thread from async contexts."""
    client = get_client()
    try:
        response = client.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=True,
        )
        hits = response.points
    except AttributeError:
        hits = client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=True,
        )
    results = []
    for hit in hits:
        if not hit.payload:
            continue
        vector = hit.vector if isinstance(hit.vector, list) else list(hit.vector.values())[0] if isinstance(hit.vector, dict) else []
        results.append({
            "text":   hit.payload.get("text", ""),
            "source": hit.payload.get("source", "unknown"),
            "tag":    hit.payload.get("tag", "general"),
            "score":  round(hit.score, 4),
            "vector": vector,
        })
    return results


def retrieve_context_with_sources(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.20,
) -> list[dict]:
    """
    Synchronous entry point (called via asyncio.to_thread from agents).
    Hybrid: dense + BM25 → RRF → MMR.
    Returns list of {text, source, tag, score, retrieval_method} dicts.
    """
    if not _check_collection_has_data():
        return []

    try:
        from backend.rag.bm25_retriever import get_index
        from backend.rag.embeddings import EmbeddingModel

        embedder = EmbeddingModel.get_instance()
        query_vector = embedder.embed_one(query)

        dense = _vector_search(query_vector, top_k=top_k * 3, score_threshold=score_threshold)
        bm25 = get_index().search(query, k=top_k * 3)

        from backend.rag.hybrid_retriever import _rrf_fuse
        fused = _rrf_fuse(dense, bm25, alpha=0.5)

        if not fused:
            return []

        # Add vectors for MMR (dense results already have them)
        for doc in fused:
            if "vector" not in doc:
                doc["vector"] = embedder.embed_one(doc["text"])

        selected = mmr_select(fused, top_k=top_k, lambda_mult=0.6)
        return selected

    except Exception as e:
        # Fall back to pure dense if hybrid fails
        logger.warning("Hybrid retrieval fell back to dense: %s", e)
        from backend.rag.embeddings import EmbeddingModel
        embedder = EmbeddingModel.get_instance()
        query_vector = embedder.embed_one(query)
        candidates = _vector_search(query_vector, top_k=top_k * 3, score_threshold=score_threshold)
        return mmr_select(candidates, top_k=top_k, lambda_mult=0.6) if candidates else []


async def retrieve_context_multi_query(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.20,
    compress: bool = True,
) -> list[dict]:
    """
    Async entry point: multi-query expansion + hybrid retrieval + optional compression.
    Rewrites query → variants → parallel hybrid search → RRF merge → MMR → compress.
    """
    if not _check_collection_has_data():
        return []

    from backend.rag.query_rewriter import rewrite_query
    from backend.rag.hybrid_retriever import retrieve_hybrid

    queries = await rewrite_query(query)

    # Run hybrid search for each query variant in parallel
    search_tasks = [
        retrieve_hybrid(q, top_k=top_k * 2, score_threshold=score_threshold)
        for q in queries
    ]
    all_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    seen_texts: set[str] = set()
    all_candidates: list[dict] = []
    for res in all_results:
        if isinstance(res, Exception):
            continue
        for r in res:
            if r["text"] not in seen_texts:
                seen_texts.add(r["text"])
                all_candidates.append(r)

    if not all_candidates:
        return []

    from backend.rag.embeddings import EmbeddingModel
    embedder = EmbeddingModel.get_instance()
    for doc in all_candidates:
        if "vector" not in doc:
            doc["vector"] = await asyncio.to_thread(embedder.embed_one, doc["text"])

    selected = mmr_select(all_candidates, top_k=top_k, lambda_mult=0.6)

    # Optional context compression (reduces token usage ~50%)
    if compress and selected:
        from backend.rag.compressor import compress_chunks
        try:
            selected = await compress_chunks(selected, query)
        except Exception as e:
            logger.warning("Compression skipped: %s", e)

    return selected


# ─── Legacy sync helper (kept for backwards compat with old /rag/query) ───────

def retrieve_context(query: str, top_k: int = 5, score_threshold: float = 0.35) -> list[str]:
    """Returns plain text list — used by old code paths."""
    results = retrieve_context_with_sources(query, top_k, score_threshold)
    return [r["text"] for r in results]
