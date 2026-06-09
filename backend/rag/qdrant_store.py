from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from backend.config import settings

_client: QdrantClient | None = None

VECTOR_SIZE = 384  # BAAI/bge-small-en-v1.5 output dimensions


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        if settings.QDRANT_LOCAL_PATH:
            _client = QdrantClient(path=settings.QDRANT_LOCAL_PATH)
            print(f"Qdrant: local embedded mode → '{settings.QDRANT_LOCAL_PATH}'")
        elif settings.QDRANT_URL:
            # Qdrant Cloud (production)
            _client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
            )
            print(f"Qdrant: cloud → {settings.QDRANT_URL}")
        else:
            _client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
            print(f"Qdrant: self-hosted → {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    return _client


def init_collection() -> None:
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"Qdrant: created collection '{settings.QDRANT_COLLECTION}'")
    else:
        print(f"Qdrant: collection '{settings.QDRANT_COLLECTION}' already exists")
