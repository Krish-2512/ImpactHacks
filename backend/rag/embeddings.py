from typing import List
from fastembed import TextEmbedding


class EmbeddingModel:
    _instance: "EmbeddingModel | None" = None

    def __init__(self):
        # Downloads ~40MB BAAI/bge-small-en-v1.5 on first run, then caches
        self.model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    @classmethod
    def get_instance(cls) -> "EmbeddingModel":
        if cls._instance is None:
            cls._instance = EmbeddingModel()
        return cls._instance

    def embed(self, texts: List[str]) -> List[List[float]]:
        return list(self.model.embed(texts))

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]
