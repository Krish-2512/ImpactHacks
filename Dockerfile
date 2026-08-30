# ── Stage 1: builder — install heavy dependencies ────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps for numpy/pandas/statsmodels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install into a local prefix so we can copy only installed packages
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY backend/   ./backend/

# Create directories needed at runtime (ml_data trains on startup, rag_data ingested separately)
RUN mkdir -p qdrant_data ml_data rag_data/crop_guides rag_data/pest_control

# HuggingFace models cache inside container (disease model auto-downloads)
ENV HF_HOME=/app/.cache/huggingface
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
