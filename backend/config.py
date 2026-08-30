from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # SQL database (user storage) — SQLite by default, PostgreSQL for production
    # For PostgreSQL: DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/agrow
    DATABASE_URL: str = "sqlite+aiosqlite:///./agrow_users.db"

    # MongoDB (agent cycles, memory, notifications, marketplace)
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

    # Set to true to fetch real-time weather from Open-Meteo instead of SARIMAX/seasonal model
    USE_LIVE_WEATHER: bool = False

    # Rate limiting — requests per minute per IP (0 = disabled)
    RATE_LIMIT_RPM: int = 60

    # Email notifications via SMTP
    # Gmail: smtp.gmail.com:587 + an App Password (Google Account → Security → App passwords)
    EMAIL_NOTIFICATIONS_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""          # your Gmail address
    SMTP_PASSWORD: str = ""      # 16-char App Password (NOT your login password)
    SMTP_FROM: str = ""          # display name/address, defaults to SMTP_USER if blank
    EMAIL_MIN_PRIORITY: str = "high"  # send emails for "high" and "urgent" only

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
