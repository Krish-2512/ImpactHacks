"""
Semantic memory vector store — stores farmer memory embeddings in Qdrant.

Collection: "farmer_memory_vectors"
Each point payload: {farmer_id, cycle_id, date, memory_text, weather_summary, market_summary}

On save_memory_with_embedding(): embeds memory_text → upserts into Qdrant
On get_relevant_memories(): embeds query → ANN search → returns matching memory docs
"""
import asyncio
import uuid
from typing import Any

MEMORY_COLLECTION = "farmer_memory_vectors"
VECTOR_SIZE = 384   # BAAI/bge-small-en-v1.5


def _get_qdrant():
    from backend.rag.qdrant_store import get_client
    return get_client()


def _get_embedder():
    from backend.rag.embeddings import EmbeddingModel
    return EmbeddingModel.get_instance()


def _ensure_collection() -> None:
    from qdrant_client.models import VectorParams, Distance
    client = _get_qdrant()
    existing = [c.name for c in client.get_collections().collections]
    if MEMORY_COLLECTION not in existing:
        client.create_collection(
            collection_name=MEMORY_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


def _upsert_memory(
    farmer_id: str,
    cycle_id: str,
    memory_text: str,
    payload: dict[str, Any],
) -> None:
    """Blocking — called via asyncio.to_thread."""
    from qdrant_client.models import PointStruct

    _ensure_collection()
    embedder = _get_embedder()
    vector = embedder.embed_one(memory_text)

    point = PointStruct(
        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{farmer_id}:{cycle_id}")),
        vector=vector,
        payload={
            "farmer_id":    farmer_id,
            "cycle_id":     cycle_id,
            "memory_text":  memory_text,
            **payload,
        },
    )
    client = _get_qdrant()
    client.upsert(collection_name=MEMORY_COLLECTION, points=[point])


def _search_memories(
    farmer_id: str,
    query_vector: list[float],
    k: int,
) -> list[dict[str, Any]]:
    """Blocking — called via asyncio.to_thread."""
    _ensure_collection()
    client = _get_qdrant()
    try:
        # Try newer API first
        results = client.query_points(
            collection_name=MEMORY_COLLECTION,
            query=query_vector,
            limit=k,
            query_filter={"must": [{"key": "farmer_id", "match": {"value": farmer_id}}]},
        ).points
    except AttributeError:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        results = client.search(
            collection_name=MEMORY_COLLECTION,
            query_vector=query_vector,
            limit=k,
            query_filter=Filter(
                must=[FieldCondition(key="farmer_id", match=MatchValue(value=farmer_id))]
            ),
        )

    return [
        {
            "cycle_id":       r.payload.get("cycle_id", ""),
            "date":           r.payload.get("date", ""),
            "memory_text":    r.payload.get("memory_text", ""),
            "weather_summary": r.payload.get("weather_summary", ""),
            "market_summary":  r.payload.get("market_summary", ""),
            "recommendation_summary": r.payload.get("recommendation_summary", ""),
            "disease_alerts": r.payload.get("disease_alerts", []),
            "score":          r.score,
        }
        for r in results
    ]


# ── Public async API ──────────────────────────────────────────────────────────

async def save_memory_embedding(
    farmer_id: str,
    cycle_id: str,
    memory_text: str,
    weather_summary: str = "",
    market_summary: str = "",
    recommendation_summary: str = "",
    disease_alerts: list[str] | None = None,
    date: str = "",
) -> None:
    """
    Embed memory_text and upsert into the Qdrant memory collection.
    Silently logs failures — never crashes the pipeline.
    """
    try:
        payload = {
            "date":                   date,
            "weather_summary":         weather_summary,
            "market_summary":          market_summary,
            "recommendation_summary":  recommendation_summary,
            "disease_alerts":          disease_alerts or [],
        }
        await asyncio.to_thread(_upsert_memory, farmer_id, cycle_id, memory_text, payload)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Memory embedding save failed: %s", e)


async def get_relevant_memories(
    farmer_id: str,
    query: str,
    k: int = 8,
) -> list[dict[str, Any]]:
    """
    Semantically retrieve the k most relevant memory entries for a query.
    Falls back to empty list on any error.
    """
    try:
        embedder = _get_embedder()
        query_vector = await asyncio.to_thread(embedder.embed_one, query)
        return await asyncio.to_thread(_search_memories, farmer_id, query_vector, k)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Semantic memory retrieval failed: %s", e)
        return []
