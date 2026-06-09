from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError

from backend.database.mongodb import connect_db, close_db
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — each step is fault-tolerant so the server starts regardless
    try:
        await connect_db()
    except Exception as e:
        print(f"[WARNING] MongoDB startup error: {e}")
    try:
        ModelCache.load_all()
    except Exception as e:
        print(f"[WARNING] ML model load error: {e}")
    try:
        init_collection()
    except Exception as e:
        print(f"[WARNING] Qdrant init skipped: {e}")
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Agrow Intelligence API",
    description="Multi-agent AI system for Northeast India precision agriculture",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev
        "http://localhost:3000",   # CRA dev
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router,          prefix="/auth",          tags=["Auth"])
app.include_router(market_router,        prefix="/market",        tags=["Marketplace"])
app.include_router(predict_router,       prefix="/predict",       tags=["Predictions"])
app.include_router(disease_router,       prefix="/disease",       tags=["Disease Detection"])
app.include_router(agents_router,        prefix="/agents",        tags=["AI Agents"])
app.include_router(notifications_router, prefix="/notifications",  tags=["Notifications"])
app.include_router(rag_router,           prefix="/rag",            tags=["RAG Advisory"])
app.include_router(ml_router,            prefix="",               tags=["ML Models"])
app.include_router(translate_router,     prefix="",               tags=["Translation"])


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


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Agrow Intelligence API v2"}
