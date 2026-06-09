from typing import List
from backend.rag.embeddings import EmbeddingModel
from backend.rag.qdrant_store import get_client
from backend.config import settings


def retrieve_context(query: str, top_k: int = 5, score_threshold: float = 0.35) -> List[str]:
    embedder = EmbeddingModel.get_instance()
    query_vector = embedder.embed_one(query)

    client = get_client()

    # qdrant-client >= 1.7 renamed .search() to .query_points()
    try:
        response = client.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
        )
        hits = response.points
    except AttributeError:
        # Fallback for older qdrant-client versions
        hits = client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
        )

    return [hit.payload.get("text", "") for hit in hits if hit.payload]
