from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "agrow"

    # JWT
    SECRET_KEY: str = "changeme-generate-with-secrets-token-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Groq
    GROQ_API_KEY: str = ""
    GROQ_MODEL_FAST: str = "llama-3.1-8b-instant"
    GROQ_MODEL_POWER: str = "llama-3.3-70b-versatile"

    # Qdrant — three modes:
    #   1. Local embedded (dev):  QDRANT_LOCAL_PATH=./qdrant_data
    #   2. Docker (self-hosted):  QDRANT_LOCAL_PATH="" + QDRANT_HOST/PORT
    #   3. Qdrant Cloud (prod):   QDRANT_LOCAL_PATH="" + QDRANT_URL + QDRANT_API_KEY
    QDRANT_LOCAL_PATH: str = "./qdrant_data"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_URL: str = ""        # e.g. https://xyz.europe-west3-0.gcp.cloud.qdrant.io
    QDRANT_API_KEY: str = ""    # from Qdrant Cloud dashboard
    QDRANT_COLLECTION: str = "agrow_knowledge"

    # HuggingFace disease model
    DISEASE_MODEL_ID: str = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"

    # Weather location (Open-Meteo, free, no API key needed)
    # Default: Guwahati, Assam — change in .env for other locations
    WEATHER_LAT: float = 26.1445
    WEATHER_LON: float = 91.7362

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
