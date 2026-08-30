import logging
import logging.config
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.database.mongodb import connect_db, close_db
from backend.database.sql import init_sql
from backend.ml.model_cache import ModelCache
from backend.rag.qdrant_store import init_collection

from backend.auth.router import router as auth_router
from backend.routers.marketplace import router as market_router
from backend.routers.predictions import router as predict_router
from backend.routers.disease import router as disease_router
from backend.routers.agents import router as agents_router
from backend.routers.notifications import router as notifications_router
from backend.routers.rag import router as rag_router
from backend.routers.ml_extra import router as ml_router
from backend.routers.translate import router as translate_router
from backend.routers.intelligence import router as intelligence_router
from backend.routers.observability import router as observability_router
from backend.routers.evaluation import router as evaluation_router

# ── Structured logging (replaces print() throughout the app) ───────────────────
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "httpx": {"level": "WARNING"},
        "httpcore": {"level": "WARNING"},
        "groq":     {"level": "WARNING"},
    },
})


_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — each step is fault-tolerant so the server starts regardless
    try:
        await init_sql()
        _log.info("SQL database initialised (users table ready)")
    except Exception as e:
        _log.warning("SQL init error: %s", e)
    try:
        await connect_db()
    except Exception as e:
        _log.warning("MongoDB startup error: %s", e)
    try:
        ModelCache.load_all()
    except Exception as e:
        _log.warning("ML model load error: %s", e)
    try:
        init_collection()
        # Auto-ingest knowledge base on first run (when collection is empty)
        await _auto_ingest_if_empty()
    except Exception as e:
        _log.warning("Qdrant init skipped: %s", e)
    yield
    await close_db()


async def _auto_ingest_if_empty() -> None:
    """Ingest rag_data/ into Qdrant if the collection has no vectors yet."""
    import asyncio
    from pathlib import Path
    from backend.rag.retriever import _check_collection_has_data

    if _check_collection_has_data():
        _log.info("Qdrant collection already has data — skipping auto-ingest")
        return

    rag_data = Path(__file__).parent.parent / "rag_data"
    if not rag_data.exists():
        _log.warning("rag_data/ not found — skipping auto-ingest")
        return

    _log.info("Knowledge base is empty — starting background ingestion from %s", rag_data)

    def _ingest():
        from backend.rag.ingestor import ingest_directory
        total = 0
        for subdir in sorted(rag_data.iterdir()):
            if subdir.is_dir():
                n = ingest_directory(subdir, tag=subdir.name)
                _log.info("Ingested %d chunks from rag_data/%s/", n, subdir.name)
                total += n
        _log.info("Auto-ingest complete: %d total chunks", total)

    # Run blocking ingest in thread pool so startup is not delayed
    asyncio.get_event_loop().run_in_executor(None, _ingest)


# Rate limiter — 60 req/min per IP by default (configurable via RATE_LIMIT_RPM in .env)
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="Agrow Intelligence API",
    description="Multi-agent AI system for Northeast India precision agriculture",
    version="2.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router,          prefix="/auth",          tags=["Auth"])
app.include_router(market_router,        prefix="/market",        tags=["Marketplace"])
app.include_router(predict_router,       prefix="/predict",       tags=["Predictions"])
app.include_router(disease_router,       prefix="/disease",       tags=["Disease Detection"])
app.include_router(agents_router,        prefix="/agents",        tags=["AI Agents"])
app.include_router(notifications_router, prefix="/notifications",  tags=["Notifications"])
app.include_router(rag_router,           prefix="/rag",           tags=["RAG Advisory"])
app.include_router(ml_router,            prefix="",               tags=["ML Models"])
app.include_router(translate_router,     prefix="",               tags=["Translation"])
app.include_router(intelligence_router,  prefix="/intelligence",  tags=["Agriculture Intelligence"])
app.include_router(observability_router, prefix="/observability", tags=["Observability"])
app.include_router(evaluation_router,    prefix="/evaluation",    tags=["Evaluation"])


@app.exception_handler(ServerSelectionTimeoutError)
async def mongo_timeout_handler(_request: Request, _exc: ServerSelectionTimeoutError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable. Configure MONGODB_URI in .env and restart."},
    )


@app.exception_handler(PyMongoError)
async def mongo_error_handler(_request: Request, exc: PyMongoError):
    return JSONResponse(
        status_code=503,
        content={"detail": f"Database error: {exc}"},
    )


@app.get("/")
async def root():
    return {"service": "Agrow Intelligence API v2.1", "docs": "/docs", "health": "/health"}


@app.get("/health")
async def health():
    from backend.ml.model_cache import ModelCache
    cache = ModelCache.get()
    return {
        "status": "ok",
        "service": "Agrow Intelligence API v2.1",
        "models_loaded": cache is not None,
    }
