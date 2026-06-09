# Agrow Intelligence v2

> AI-powered agricultural intelligence platform for Northeast India farmers.  
> An upgraded rebuild of [ImpactHacks (v1)](https://github.com/Krish-2512/ImpactHacks/tree/main) — migrated from Django monolith to a production-grade FastAPI + React + multi-model ML system.

---

## What's New in v2

| Feature | v1 (ImpactHacks) | v2 (Agrow Intelligence) |
|---------|------------------|------------------------|
| Backend | Django monolith | FastAPI async REST API |
| Frontend | HTML/CSS/JS templates | React 19 SPA + Tailwind CSS |
| ML Models | 2 (SARIMAX + XGBoost) | 8 models across 5 domains |
| AI Agents | None | 5-agent LangGraph pipeline (Groq LLaMA) |
| Language Support | English only | 7 languages with live neural translation |
| Database | SQLite | MongoDB Atlas |
| Vector Search | None | Qdrant RAG pipeline |
| Plant Disease | None | MobileNetV2 (38 disease classes) |
| Deployment | Local only | Docker + Render + Vercel + CI/CD |

---

## Features

- **AI Agent Pipeline** — 5 LangGraph agents (Fetching → Weather → Market → Advisory → Supervisor) powered by Groq LLaMA-3 generate a full farm intelligence report on demand
- **8 ML Models** — SARIMAX weather forecasting, XGBoost weather classification, SARIMAX crop price forecasting, Random Forest crop recommender, Decision Tree irrigation advisor, Isolation Forest price anomaly detector, MobileNetV2 disease detector
- **RAG Advisory** — FastEmbed + Qdrant vector search over ICAR agricultural knowledge base; answers crop and pest management queries
- **Plant Disease Detection** — Upload a leaf image, get disease name + treatment in under 2 seconds
- **Live Marketplace** — Farmers list produce; buyers browse and purchase; real-time transaction history
- **Multi-language UI** — Google Translate integration for Hindi, Bengali, Assamese, Nepali, Mizo, Manipuri with localStorage caching

---

## Tech Stack

### Backend
- **FastAPI** + **Uvicorn** — async REST API
- **MongoDB Atlas** + **Motor** — async document database
- **LangGraph** + **LangChain** + **Groq API** — multi-agent orchestration (LLaMA-3.1-8b-instant + LLaMA-3.3-70b-versatile)
- **FastEmbed** (BAAI/bge-small-en-v1.5) + **Qdrant** — RAG vector search
- **python-jose** + **passlib** — JWT authentication

### Machine Learning
| Model | Algorithm | Purpose |
|-------|-----------|---------|
| Weather Forecaster | SARIMAX (4 vars) | 7-day temperature, humidity, wind, precipitation |
| Weather Classifier | XGBoost | Sunny / Cloudy / Rainy / Stormy label |
| Crop Price Forecaster | SARIMAX (4 crops) | Daily price prediction (brinjal, cabbage, lemon, tomato) |
| Crop Recommender | Random Forest (200 trees) | Top-3 crops from N/P/K/soil/climate inputs |
| Irrigation Advisor | Decision Tree | Should irrigate + recommended mm, FAO-based |
| Price Anomaly Detector | Isolation Forest (150 trees) | Flags abnormal market prices |
| Seasonal Price Model | Statistical (12-month multipliers) | 6 additional crops |
| Disease Detector | MobileNetV2 (fine-tuned) | 38 PlantVillage disease classes |

### Frontend
- **React 19** + **Vite** + **Tailwind CSS**
- **TanStack Query** — server state, caching, background refetch
- **Zustand** — auth + agent report global state
- **Recharts** — interactive charts (price trends, weather, confidence bars)
- **i18next** + **Google Translate API** — runtime language switching
- **Framer Motion** — animations

### DevOps
- **Docker** — multi-stage build (builder + runtime), ~300MB image
- **Render** — free-tier backend hosting (Docker runtime)
- **Vercel** — frontend hosting
- **GitHub Actions** — CI/CD: lint → build → Docker build → Render deploy hook

---

## Architecture

```
User Request
     │
     ▼
React SPA (Vercel)
     │  HTTPS
     ▼
FastAPI Backend (Render / Docker)
     ├── Auth Router         → MongoDB Atlas
     ├── Predict Router      → ModelCache (pkl in memory)
     ├── Agents Router       → LangGraph → Groq LLaMA-3
     │                           ├── Fetching Agent (ML data)
     │                           ├── Weather Agent (LLM interpretation)
     │                           ├── Market Agent (sell/hold decisions)
     │                           ├── Advisory Agent (RAG + LLM)
     │                           └── Supervisor Agent (final report)
     ├── RAG Router          → FastEmbed → Qdrant
     ├── Disease Router      → MobileNetV2 (HuggingFace)
     ├── Marketplace Router  → MongoDB Atlas
     └── Translate Router    → Google Translate API
```

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (for Qdrant)

### 1. Clone and configure

```bash
git clone https://github.com/Krish-2512/ImpactHacks.git -b agrow-v2
cd ImpactHacks
cp .env.example .env
# Fill in .env with your MongoDB URI, Groq API key, Secret key
```

### 2. Start Qdrant (vector DB)

```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

### 3. Install and run backend

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Backend runs at `http://localhost:8000` — Swagger docs at `/docs`

### 4. Ingest RAG knowledge base (one-time)

```bash
python -m backend.rag.ingestor
```

### 5. Install and run frontend

```bash
cd frontend
cp .env.example .env       # VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

---

## Environment Variables

### Backend `.env`

```
MONGODB_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/agrow
MONGODB_DB_NAME=agrow
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_hex(32))">
GROQ_API_KEY=gsk_...
GROQ_MODEL_FAST=llama-3.1-8b-instant
GROQ_MODEL_POWER=llama-3.3-70b-versatile
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=agrow_knowledge
```

### Frontend `frontend/.env`

```
VITE_API_URL=http://localhost:8000
```

---

## Deployment

### Backend → Render (free tier)

1. Push to GitHub (`agrow-v2` branch)
2. New Web Service on [render.com](https://render.com) → connect repo → branch: `agrow-v2`
3. Render auto-detects `render.yaml` (Docker runtime)
4. Add environment variable secrets in Render dashboard
5. Auto-deploys on every push via GitHub Actions

### Frontend → Vercel (free tier)

1. New project on [vercel.com](https://vercel.com) → connect same repo
2. Root Directory: `frontend`, Branch: `agrow-v2`
3. Add `VITE_API_URL=https://your-service.onrender.com`
4. Deploy

### Vector DB → Qdrant Cloud (free tier)

1. Free cluster at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Set `QDRANT_URL` and `QDRANT_API_KEY` in Render environment
3. Run `python -m backend.rag.ingestor` once locally (points to cloud)

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register farmer/buyer |
| POST | `/auth/login` | JWT login |
| GET | `/predict/weather` | 7-day SARIMAX forecast |
| GET | `/predict/prices` | Crop price forecast |
| POST | `/ml/recommend-crop` | Top-3 crop recommendations |
| POST | `/ml/irrigation` | Irrigation decision + mm |
| GET | `/ml/price-anomaly` | Anomaly detection on today's prices |
| GET | `/ml/model-info` | All 8 model metadata |
| POST | `/agents/run-cycle` | Trigger full AI agent analysis |
| GET | `/agents/latest-report` | Most recent LLM-generated report |
| POST | `/disease/detect` | Plant disease from leaf image |
| POST | `/rag/query` | RAG-powered crop advisory |
| POST | `/translate/` | Batch translate UI strings |
| GET | `/market/products` | Browse marketplace listings |
| POST | `/market/products/{id}/purchase` | Buy produce |

Full interactive docs: `/docs`

---

## Project Structure

```
agrow-v2/
├── backend/
│   ├── agents/          # LangGraph 5-agent pipeline
│   ├── auth/            # JWT authentication
│   ├── disease/         # MobileNetV2 plant disease detector
│   ├── integrations/    # Google Translate client
│   ├── ml/              # 8 ML models + ModelCache singleton
│   ├── rag/             # FastEmbed + Qdrant RAG pipeline
│   └── routers/         # FastAPI route handlers
├── frontend/
│   └── src/
│       ├── api/         # Axios API clients
│       ├── hooks/       # useAutoTranslate, custom hooks
│       ├── pages/       # 11 pages
│       └── store/       # Zustand state
├── rag_data/            # ICAR agricultural knowledge base (.txt)
├── Dockerfile           # Multi-stage Docker build
├── render.yaml          # Render IaC deployment config
└── .github/workflows/   # GitHub Actions CI/CD
```

---

## Branch History

| Branch | Description |
|--------|-------------|
| `main` | v1 — Django hackathon prototype (ImpactHacks) |
| `agrow-v2` | v2 — Production rebuild (this branch) |

---

## License

MIT
