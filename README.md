# Agrow Intelligence

> AI-powered agricultural intelligence platform for Northeast India farmers.  
> Combines classical time-series forecasting, ensemble machine learning, deep learning, large language models, retrieval-augmented generation, and explainable AI into a single production system.

---

## Table of Contents

1. [What This System Does](#1-what-this-system-does)
2. [Machine Learning Models](#2-machine-learning-models)
3. [AI Agent Pipeline](#3-ai-agent-pipeline)
4. [RAG Advisory System](#4-rag-advisory-system)
5. [Plant Disease Detection](#5-plant-disease-detection)
6. [Explainable AI — SHAP](#6-explainable-ai--shap)
7. [Causal Inference Research](#7-causal-inference-research)
8. [Backend Architecture](#8-backend-architecture)
9. [Frontend](#9-frontend)
10. [Database Design](#10-database-design)
11. [Local Setup](#11-local-setup)
12. [Environment Variables](#12-environment-variables)
13. [Deployment](#13-deployment)
14. [API Reference](#14-api-reference)
15. [Project Structure](#15-project-structure)

---

## 1. What This System Does

Agrow Intelligence is a full-stack AI platform built for smallholder farmers in Northeast India (Assam, Manipur, Meghalaya, and surrounding states). The system:

- **Predicts** weather (temperature, humidity, wind, precipitation) and crop market prices 7 days ahead using SARIMAX time-series models trained on regional historical data
- **Recommends** which crop to plant based on current soil chemistry (NPK) and microclimate using a Random Forest classifier trained on ICAR agronomic parameters
- **Explains** every crop recommendation using SHAP (SHapley Additive exPlanations) — showing exactly which soil or climate factor drove the model's decision
- **Advises** on irrigation scheduling per crop and growth stage using a Decision Tree trained on FAO evapotranspiration rules
- **Detects** abnormal price movements in 10 crop markets using Isolation Forest anomaly detection
- **Identifies** plant diseases from leaf photographs using a fine-tuned MobileNetV2 CNN (38 disease classes from PlantVillage)
- **Runs** a 5-agent LangGraph pipeline powered by Groq's LLaMA-3 models to generate a comprehensive farm intelligence report combining all data streams
- **Answers** crop management questions using Retrieval-Augmented Generation over an ICAR agricultural knowledge base
- **Translates** the entire UI into 7 languages including Hindi, Bengali, Assamese, and Manipuri
- **Connects** farmers to buyers through an integrated marketplace with real-time transaction tracking

---

## 2. Machine Learning Models

### 2.1 SARIMAX Weather Forecaster

**Algorithm:** Seasonal AutoRegressive Integrated Moving Average with eXogenous inputs (SARIMAX)  
**Library:** `statsmodels`

SARIMAX is a univariate time-series model that extends ARIMA with:
- **Seasonal terms** (P, D, Q, s) to capture annual/monthly agricultural weather cycles in Northeast India
- **Exogenous regressors** — allows other variables (e.g., monsoon index) to influence the forecast

Four separate SARIMAX models are trained, one per output variable:
- Temperature (°C)
- Humidity (%)
- Wind Speed (km/h)
- Precipitation (mm)

The models learn from historical weather data for the Guwahati / Assam region. On Render's ephemeral filesystem (where pkl files are lost on restart), a **deterministic seasonal fallback** is used — a cosine function parameterized by day-of-year that approximates regional seasonal patterns:

```
temp(d) = 26 + 8 × cos(2π × (d - 200) / 365)
```

### 2.2 XGBoost Weather Classifier

**Algorithm:** Extreme Gradient Boosting (XGBoost)  
**Library:** `xgboost`

After the SARIMAX models predict numeric weather variables, a multi-class XGBoost classifier maps those values to a human-readable weather condition label:

> `Sunny | Partly Cloudy | Cloudy | Overcast | Drizzle | Rainy | Heavy Rain | Stormy`

XGBoost builds an ensemble of gradient-boosted decision trees. Each tree corrects the residual errors of the previous one. The model uses:
- **Features:** Temperature, Humidity, Wind Speed, Precipitation
- **Objective:** `multi:softprob` (returns class probabilities)
- **Depth:** 4 levels (shallow to avoid overfitting on small meteorological dataset)

A **rule-based fallback** is also implemented for when the XGBoost pkl is unavailable — maps precipitation thresholds directly to condition labels.

### 2.3 SARIMAX Crop Price Forecaster

**Algorithm:** SARIMAX (same as Weather Forecaster)  
**Crops:** Brinjal, Cabbage, Lemon, Tomato

Four independent SARIMAX models forecast daily market prices (INR/quintal) for the four primary cash crops of Northeast India. The models capture:
- Long-term price trends (harvest season vs. off-season)
- Weekly market-day cycles
- Monsoon-season price spikes (transport disruption)

**Seasonal fallback formula** (used when pkl unavailable):
```
price(month, doy) = base_price × seasonal_multiplier[month] × (1 + 0.04 × sin(2π × doy/365))
```
Each crop has a hand-tuned `base_price` and 12 monthly multipliers derived from AGMARKNET historical data.

### 2.4 Seasonal Price Calculator

**Algorithm:** Deterministic multiplicative seasonal model  
**Crops:** Potato, Onion, Ginger, Turmeric, Chili, Garlic

Six additional crops use a lightweight statistical model with hard-coded base prices and 12-month seasonal multipliers. This avoids the overhead of training 6 more SARIMAX models while still producing agronomically sensible price forecasts (garlic is cheap in winter harvest, expensive pre-monsoon, etc.).

### 2.5 Random Forest Crop Recommender

**Algorithm:** Random Forest Classifier (200 trees)  
**Library:** `scikit-learn`  
**Input features:** N, P, K (kg/ha), Temperature (°C), Humidity (%), Soil pH, Rainfall (mm/year)  
**Output:** Top-3 crops with confidence scores and suitability rating

A Random Forest is an ensemble of decision trees where:
- Each tree is trained on a **bootstrap sample** of the training data (bagging)
- Each split considers a **random subset of features** (feature randomization)
- Final prediction = majority vote (classification) across all 200 trees

**Training data** is generated synthetically from ICAR agronomic parameter tables for 10 Northeast India crops:

| Crop | Ideal N (kg/ha) | Ideal pH | Ideal Rainfall (mm) |
|------|-----------------|----------|---------------------|
| Tomato | 60–80 | 6.0–7.0 | 600–1200 |
| Brinjal | 80–100 | 5.5–6.6 | 600–1200 |
| Cabbage | 100–120 | 6.0–7.5 | 300–500 |
| Lemon | 60–80 | 5.5–7.0 | 750–1250 |
| Potato | 80–100 | 5.0–6.5 | 500–700 |
| Onion | 60–80 | 6.0–7.0 | 350–550 |
| Ginger | 60–80 | 5.5–6.5 | 1500–3000 |
| Turmeric | 60–80 | 4.5–7.5 | 1500–2500 |
| Chili | 80–100 | 6.0–7.0 | 600–1200 |
| Garlic | 60–80 | 6.0–7.0 | 250–500 |

3,500 training samples total (350 per crop, 70% uniform within ideal range + 30% Gaussian fringe to allow natural class overlap). Test accuracy on held-out synthetic data exceeds 92%.

### 2.6 Decision Tree Irrigation Advisor

**Algorithm:** Decision Tree Classifier + Regressor  
**Library:** `scikit-learn`

A two-stage Decision Tree model:
1. **Classifier** — decides `irrigate | skip | urgent`
2. **Regressor** — recommends how many mm of water to apply

**Feature inputs:**
- Crop species (one-hot encoded: 10 crops)
- Growth stage (`seedling | vegetative | flowering | fruiting`)
- Days since last rainfall
- Rainfall this week (mm)
- Current temperature (°C)
- Current humidity (%)

Decision rules are derived from **FAO Irrigation and Drainage Paper No. 56** (crop coefficient method). For example, flowering-stage tomato in >28°C with >5 dry days triggers an `urgent` irrigation with 25–30 mm recommendation.

Decision Trees are used here (rather than Random Forest) because interpretability matters — farmers or extension workers can follow the tree logic manually to verify the advice.

### 2.7 Isolation Forest Price Anomaly Detector

**Algorithm:** Isolation Forest (150 trees)  
**Library:** `scikit-learn`  
**Contamination rate:** 5%

Isolation Forest detects price anomalies without any labels. It works by:
1. Randomly selecting a feature and a split value
2. Recursively partitioning data until each point is isolated
3. **Anomalies are isolated faster** (shorter average path length) because they lie in sparse regions of the feature space

**Training data:** 730 days of synthetic price data for all 10 crops, generated with realistic seasonal patterns and occasional injected spikes (+40–80% above seasonal baseline).

The model flags prices that deviate significantly from the expected seasonal range and returns:
- `is_anomaly: true/false` per crop
- `anomaly_score` (-1 to 1, lower = more anomalous)
- Human-readable alert message for any flagged crops

### 2.8 MobileNetV2 Plant Disease Detector

**Algorithm:** MobileNetV2 (Convolutional Neural Network)  
**Framework:** HuggingFace Transformers + PyTorch  
**Model:** `linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification`  
**Dataset:** PlantVillage (54,306 leaf images, 38 disease classes)

MobileNetV2 uses **depthwise separable convolutions** — factoring a standard convolution into a depthwise (spatial filtering) and pointwise (feature combining) step. This reduces computation by ~8–9× compared to a standard CNN at similar accuracy.

The model is fine-tuned on PlantVillage which covers:
- 14 crop species (tomato, potato, pepper, apple, corn, grape, etc.)
- 26 disease classes + 12 healthy classes

**Output for each uploaded image:**
- Crop species (`tomato`, `potato`, `pepper bell`, ...)
- Disease name (`Late Blight`, `Early Blight`, `Bacterial Spot`, ...)
- Confidence score (%)
- Treatment recommendation (mapped from a 38-entry treatment dictionary)
- Top-3 alternative predictions

The model is **lazy-loaded** — weights (~14MB) download from HuggingFace on first inference request, not at server startup, to conserve the 512MB RAM on Render's free tier.

---

## 3. AI Agent Pipeline

The 5-agent LangGraph pipeline generates a comprehensive farm intelligence report by orchestrating multiple AI components in sequence.

```
Fetching Agent → Weather Agent → Market Agent → Advisory Agent → Supervisor Agent
     (data)        (LLM interp)    (LLM analysis)   (RAG + LLM)     (LLM synthesis)
```

**Framework:** LangGraph (directed state machine)  
**LLM provider:** Groq API (free tier, sub-500ms inference)  
**Models used:**
- `llama-3.1-8b-instant` — fast agent for data-heavy tasks
- `llama-3.3-70b-versatile` — powerful model for analysis and synthesis

### Agent 1 — Fetching Agent
No LLM. Pure data collection:
- Calls `ModelCache` to get today's weather forecast (SARIMAX)
- Calls `ModelCache` to get current crop prices (SARIMAX)
- Queries MongoDB for 30-day price history (for trend analysis)
- Reads user's farm profile (primary crops, location, farm size)
- Generates a unique `cycle_id` (UUID) for this analysis run

### Agent 2 — Weather Agent
**LLM:** `llama-3.1-8b-instant`  
**System prompt:** Expert agricultural meteorologist for Northeast India

Receives the numeric weather forecast and produces:
- Plain-language interpretation of the 7-day forecast
- Crop-specific planting advice (e.g., "avoid transplanting tomatoes — heavy rain expected")
- Irrigation scheduling advice based on precipitation forecast
- Urgent weather alerts (frost risk, hailstorm probability, flood warning)

### Agent 3 — Market Agent
**LLM:** `llama-3.3-70b-versatile`  
**System prompt:** Agricultural market analyst specializing in Northeast India commodity markets

Receives current prices + 30-day history and produces:
- Per-crop `SELL / HOLD / WAIT` decision with reasoning
- Price trend analysis (is the market rising or falling?)
- Best projected selling window for each crop
- Price alerts for anomalous movements (triggered by Isolation Forest output)

### Agent 4 — Advisory Agent
**LLM:** `llama-3.1-8b-instant` + **RAG**  
**System prompt:** Expert agricultural advisor for Northeast Indian farmers

Automatically generates a search query from the farm context (crops + weather condition), retrieves the top-5 most relevant chunks from the Qdrant vector database, then asks the LLM to synthesize those knowledge base excerpts into:
- Today's top cultivation advice for the farmer's specific crops
- Pest and disease warnings given current weather (high humidity → fungal risk)
- Specific treatment or preventive actions

### Agent 5 — Supervisor Agent
**LLM:** `llama-3.3-70b-versatile`  
**System prompt:** Senior agricultural intelligence coordinator

Receives all 4 agents' outputs and synthesizes:
- Executive Summary (2–3 sentences)
- Top 5 prioritized action items for the farmer today
- Critical alerts list (weather + market + disease risk combined)
- 7-day outlook narrative

The complete `AgentCycleDocument` is saved to MongoDB for historical access.

---

## 4. RAG Advisory System

**Retrieval-Augmented Generation** grounds the LLM's advice in verified agricultural knowledge rather than relying solely on training data.

**Stack:** FastEmbed (`BAAI/bge-small-en-v1.5`, 384-dim) + Qdrant vector database

### How It Works

1. **Ingestion** (one-time setup): ICAR crop guides and pest management documents are chunked into 512-word segments with 64-word overlap, embedded using FastEmbed's lightweight transformer, and stored as vectors in Qdrant
2. **Retrieval** (every advisory request): The query (auto-generated from farm context) is embedded and compared against all stored vectors using cosine similarity; top-5 chunks above a 0.35 score threshold are returned
3. **Generation**: The retrieved chunks are injected into the LLM prompt as grounding context

**Memory optimization:** FastEmbed (BAAI/bge-small-en-v1.5, ~130MB) is **not loaded at startup**. The retriever checks the Qdrant collection's point count first — if the collection is empty (no documents ingested), it returns immediately without loading the model, saving ~130MB RAM on Render's free tier.

---

## 5. Plant Disease Detection

Farmers upload a photo of a diseased leaf. The pipeline:

1. **Preprocessing:** Image is resized to 224×224, normalized with ImageNet mean/std
2. **Inference:** MobileNetV2 forward pass returns logits over 38 classes
3. **Post-processing:** Softmax probabilities; top-3 predictions extracted
4. **Treatment lookup:** Label mapped to treatment recommendation via `TREATMENT_MAP` dict (compiled from ICAR pest management guidelines)
5. **Response:** `{crop, disease, confidence, is_healthy, severity, treatment, all_predictions}`

**38 PlantVillage classes include:**
- Tomato: Early Blight, Late Blight, Leaf Mold, Mosaic Virus, Yellow Leaf Curl Virus, Septoria Leaf Spot, Spider Mites, Target Spot, Bacterial Spot, Healthy
- Potato: Early Blight, Late Blight, Healthy
- Pepper Bell: Bacterial Spot, Healthy
- Plus Apple, Cherry, Corn, Grape, Orange, Peach, Raspberry, Soybean, Squash, Strawberry diseases

---

## 6. Explainable AI — SHAP

**SHAP (SHapley Additive exPlanations)** makes the Random Forest crop recommender interpretable by showing how much each input feature contributed to a specific prediction.

### Theory

SHAP is based on **Shapley values** from cooperative game theory. Each feature is treated as a "player" in a coalition game. The Shapley value of feature *i* is the average marginal contribution of that feature across all possible orderings of all features — the fairest way to attribute prediction credit.

For tree-based models, `shap.TreeExplainer` computes exact Shapley values in O(TLD²) time (T = trees, L = leaves, D = depth) by efficiently traversing the tree structure rather than the exponential O(2^n) brute-force approach.

### What It Shows

After every crop recommendation, the API returns per-feature SHAP values for the top-recommended crop:

```json
{
  "crop": "ginger",
  "contributions": {
    "rainfall": 0.2341,
    "humidity": 0.1823,
    "temperature": 0.0934,
    "pH": -0.0512,
    "N": 0.0341,
    "K": 0.0201,
    "P": -0.0089
  },
  "base_value": 0.1,
  "predicted_probability": 78.4
}
```

- **Positive value** = this feature pushed the model toward recommending this crop
- **Negative value** = this feature pushed against this crop
- **base_value** = the model's average output for this class across all training data (baseline)
- **Final probability** = base_value + sum(all contributions)

### Frontend Visualization

The SHAP Explanation panel on the Crop Recommender page renders a **force-plot style horizontal bar chart**:
- Green bars extend right (positive contribution → pushed toward this crop)
- Red bars extend left (negative contribution → pushed away from this crop)
- Bars sorted by absolute magnitude (biggest driver at top)
- Shows the exact contribution percentage next to each bar

---

## 7. Causal Inference Research

`research/causal_price_analysis.py` demonstrates that naive correlation between rainfall and crop prices is misleading — the actual causal pathway is indirect.

**Library:** DoWhy  
**Method:** DAG-based causal modelling

### Causal DAG

```
rainfall_mm ──────────────────────────────────────────────→ price_inr (via supply)
     │                                                              ↑
     └──→ yield_qtl_ha ──────────────────────────────────→ price_inr
                                                                    ↑
temperature_c ──→ yield_qtl_ha                                      │
temperature_c ─────────────────────────────────────────────────────→│
market_demand ─────────────────────────────────────────────────────→│
input_cost ────────────────────────────────────────────────────────→│
```

### Why This Matters

A naive ML model trained on `(rainfall, price)` pairs sees a correlation and attributes direct causal power to rainfall. But the actual mechanism is:

> More rainfall → higher yield → increased supply → lower market price

Failing to model `yield` as a mediator leads to **spurious price predictions** when, for example, a drought reduces rainfall but supply remains high due to irrigation — the naive model would incorrectly predict high prices.

### Refutation Tests

The script runs 3 DoWhy refutation tests to validate the causal estimate:
1. **Add random confounder** — ATE should barely change if the model is correctly specified
2. **Placebo treatment** (permuted rainfall) — ATE should collapse to ~0 (random noise has no effect)
3. **Data subset** (80% of data) — ATE should remain stable (robust to sampling)

---

## 8. Backend Architecture

```
FastAPI Application (backend/main.py)
│
├── Lifespan startup:
│   ├── connect_db()           → Motor async MongoDB connection
│   ├── ModelCache.load_all()  → loads all ML pkl files into memory
│   ├── init_qdrant()          → creates vector collection if missing
│   └── APScheduler            → runs agent pipeline daily at 6:00 AM IST
│
├── Routers:
│   ├── /auth        → JWT register / login / me
│   ├── /predict     → SARIMAX weather + price forecasts
│   ├── /ml          → crop recommender, irrigation, anomaly, model-info
│   ├── /agents      → trigger pipeline, get latest report, history
│   ├── /disease     → MobileNetV2 leaf image inference
│   ├── /rag         → query advisory, ingest documents
│   ├── /market      → marketplace CRUD + purchase
│   ├── /notifications → read/delete notifications
│   └── /translate   → Google Translate batch
│
├── ModelCache (singleton):
│   ├── crop_price    (SARIMAX × 4)
│   ├── weather       (SARIMAX × 4 + XGBoost classifier)
│   ├── crop_recommender  (Random Forest 200 trees)
│   ├── irrigation_advisor (Decision Tree)
│   └── price_anomaly     (Isolation Forest 150 trees)
│
└── Memory management (Render 512MB free tier):
    ├── FastEmbed loads only when Qdrant collection is non-empty
    ├── MobileNetV2 loads on first disease inference request
    └── SARIMAX → seasonal formula fallback if pkl unavailable
```

**Authentication:** JWT (HS256), 60-minute expiry. Password hashing via `bcrypt` (direct, not passlib — passlib 1.7.4 is incompatible with bcrypt 4.x due to 72-byte test password limit).

**CORS:** `allow_origins=["*"]`, `allow_credentials=False` — JWT is sent via `Authorization: Bearer` header, not cookies, so wildcard origin is safe.

**Async:** All CPU-bound operations (SHAP tree traversal, FastEmbed inference, RAG retrieval) are wrapped in `asyncio.to_thread()` to avoid blocking the async event loop.

---

## 9. Frontend

**Stack:** React 19 + Vite + Tailwind CSS + TanStack Query + Zustand + Recharts + Framer Motion

### Pages

| Page | Route | Key Components |
|------|-------|----------------|
| Landing | `/` | Hero, feature cards, live stats |
| Login / Register | `/login`, `/register` | JWT auth, role selection (farmer/buyer) |
| Dashboard | `/dashboard` | Weather card, price card, Run AI Analysis button, AgentReportCard |
| Weather | `/weather` | Recharts LineChart (temp + humidity), LLM interpretation |
| Market | `/market` | Recharts AreaChart (10 crops, 30-day), sell/hold badges |
| Crop Recommender | `/recommend` | 7-parameter sliders, top-3 results, feature importance bars, SHAP force plot |
| Irrigation | `/irrigation` | Crop + stage selector, irrigation decision, mm recommendation |
| Disease | `/disease` | react-dropzone image upload, MobileNetV2 result card, treatment |
| Advisory | `/advisory` | RAG chat interface, query input, streamed LLM response |
| Marketplace | `/marketplace` | Product grid (buyer) / product form + listings (farmer) |
| Notifications | `/notifications` | Categorized alerts, mark-read, delete |

### State Management
- **Zustand** — `authStore` (JWT token + user profile, persisted to localStorage), `agentStore` (latest report, isRunning flag)
- **TanStack Query** — all server data fetching with 5-minute stale time and background refetch

### Language Support
- `i18next` + `react-i18next` for static UI strings (EN / HI base translations)
- Google Translate API integration for runtime translation of dynamic content (LLM-generated reports, crop names, treatment text) into 7 languages: Hindi, Bengali, Assamese, Nepali, Mizo, Manipuri, Bodo
- Translation results cached in `localStorage` to avoid redundant API calls

---

## 10. Database Design

**MongoDB Atlas (free tier, 512MB)**

### Collections

**`users`**
```
{ _id, username, email, hashed_password, role: "farmer"|"buyer",
  phone, location, primary_crops: [], farm_size_acres }
```

**`products`** (marketplace listings)
```
{ _id, farmer_id, farmer_name, name, price_per_unit, unit,
  quantity_available, location, is_available, created_at }
```

**`sales`** (transaction records)
```
{ _id, product_id, product_name, seller_id, buyer_id,
  quantity_sold, price_per_unit, total_amount, sold_at }
```

**`agent_cycles`** (AI analysis history)
```
{ _id, cycle_id, status: "running"|"completed"|"failed",
  weather_data, price_data, agents_output[],
  final_report, alerts[], recommendations[], created_at }
```

**`notifications`**
```
{ _id, user_id, message, message_hi, notification_type,
  severity: "info"|"warning"|"urgent", is_read, created_at }
```

---

## 11. Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for Qdrant vector database)

### 1. Clone and configure

```bash
git clone https://github.com/Krish-2512/ImpactHacks.git -b agrow-v2
cd ImpactHacks/agrow-v2
cp .env.example .env
# Edit .env — fill in MongoDB URI, Groq API key, Secret key
```

### 2. Start Qdrant

```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

### 3. Backend

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Backend: `http://localhost:8000` — Swagger UI at `/docs`

### 4. Ingest RAG knowledge base (one-time)

Place `.txt` or `.pdf` files in `rag_data/crop_guides/` and `rag_data/pest_control/`, then:

```bash
python -m backend.rag.ingestor
```

### 5. Frontend

```bash
cd frontend
cp .env.example .env.local     # set VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

Frontend: `http://localhost:5173`

### 6. Run Causal Inference Research (optional)

```bash
pip install dowhy econml
python research/causal_price_analysis.py
```

---

## 12. Environment Variables

### Backend `.env`

```
MONGODB_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/agrow
MONGODB_DB_NAME=agrow
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
GROQ_API_KEY=gsk_...
GROQ_MODEL_FAST=llama-3.1-8b-instant
GROQ_MODEL_POWER=llama-3.3-70b-versatile
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=agrow_knowledge
WEATHER_LAT=26.1445
WEATHER_LON=91.7362
DISEASE_MODEL_ID=linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification
```

For **Qdrant Cloud** (production), replace host/port with:
```
QDRANT_LOCAL_PATH=
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-key
```

### Frontend `frontend/.env.local`

```
VITE_API_URL=http://localhost:8000
```

For production, set `VITE_API_URL=https://your-service.onrender.com` in Vercel's environment variables.

---

## 13. Deployment

### Backend → Render (free tier, Docker)

1. Push to `agrow-v2` branch on GitHub
2. Create **New Web Service** on [render.com](https://render.com)
3. Connect the repo, select branch `agrow-v2` — Render auto-detects `render.yaml`
4. Add secret env vars in the Render dashboard: `MONGODB_URI`, `SECRET_KEY`, `GROQ_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`
5. Every push to `agrow-v2` triggers an auto-redeploy via GitHub Actions

### Frontend → Vercel (free tier)

1. New project on [vercel.com](https://vercel.com), connect same GitHub repo
2. Set **Root Directory** to `agrow-v2/frontend`, **Branch** to `agrow-v2`
3. Add environment variable: `VITE_API_URL=https://your-service.onrender.com`
4. Deploy — auto-redeploys on every push

### Vector DB → Qdrant Cloud (free tier)

1. Create free cluster at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Copy the cluster URL and API key into Render's environment variables
3. Ingest documents once locally (pointing `QDRANT_URL` at the cloud cluster):
   ```bash
   python -m backend.rag.ingestor
   ```

### Notes on Render Free Tier (512MB RAM)

- ML models retrain from synthetic data at startup (~15 sec) since pkl files are lost on every restart (ephemeral filesystem)
- FastEmbed skips loading if Qdrant collection is empty (saves ~130MB)
- MobileNetV2 lazy-loads on first disease request (saves ~14MB at startup)
- SARIMAX falls back to seasonal formula if pkl unavailable

---

## 14. API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | No | Register as farmer or buyer |
| POST | `/auth/login` | No | Returns JWT token |
| GET | `/auth/me` | JWT | Current user profile |
| GET | `/predict/weather` | JWT | 7-day SARIMAX weather forecast |
| GET | `/predict/prices` | JWT | Today's crop price forecast (10 crops) |
| POST | `/ml/recommend-crop` | JWT | Top-3 crops + SHAP explanation |
| POST | `/ml/irrigation` | JWT | Irrigation decision + water amount |
| GET | `/ml/price-anomaly` | JWT | Isolation Forest anomaly detection |
| GET | `/ml/model-info` | JWT | Metadata for all 8 models |
| POST | `/agents/run-cycle` | JWT | Trigger 5-agent LLM analysis (background) |
| GET | `/agents/latest-report` | JWT | Most recent agent cycle report |
| GET | `/agents/history` | JWT | All past cycle summaries |
| POST | `/disease/detect` | JWT | Plant disease from leaf image (multipart) |
| POST | `/rag/query` | JWT | RAG-powered crop advisory answer |
| POST | `/rag/ingest` | JWT | Ingest new PDF/TXT into knowledge base |
| GET | `/market/products` | JWT | Browse marketplace listings |
| POST | `/market/products` | JWT | Create product listing (farmer only) |
| POST | `/market/products/{id}/purchase` | JWT | Purchase produce (buyer only) |
| GET | `/market/transactions` | JWT | Transaction history |
| GET | `/notifications/` | JWT | User notifications |
| PUT | `/notifications/{id}/read` | JWT | Mark notification as read |
| POST | `/translate/` | JWT | Batch translate strings to target language |

Full interactive docs: `http://localhost:8000/docs`

---

## 15. Project Structure

```
agrow-v2/
├── backend/
│   ├── main.py                 # FastAPI app, lifespan, CORS, routers
│   ├── config.py               # Pydantic BaseSettings (.env loader)
│   ├── agents/
│   │   ├── graph.py            # LangGraph StateGraph definition
│   │   ├── state.py            # AgentState TypedDict
│   │   ├── fetching_agent.py   # Data collection (no LLM)
│   │   ├── weather_agent.py    # LLaMA-3.1-8b weather interpretation
│   │   ├── market_agent.py     # LLaMA-3.3-70b price analysis
│   │   ├── advisory_agent.py   # RAG + LLaMA-3.1-8b crop advice
│   │   └── supervisor_agent.py # LLaMA-3.3-70b synthesis + report
│   ├── auth/
│   │   ├── router.py           # /auth endpoints
│   │   ├── schemas.py          # Pydantic request/response models
│   │   ├── service.py          # bcrypt hashing, JWT encode/decode
│   │   └── dependencies.py     # get_current_user FastAPI dependency
│   ├── database/
│   │   └── mongodb.py          # Motor async client singleton
│   ├── disease/
│   │   └── detector.py         # MobileNetV2 inference + treatment map
│   ├── integrations/
│   │   └── translate.py        # Google Translate API client
│   ├── ml/
│   │   ├── model_cache.py      # Singleton loading all models at startup
│   │   ├── crop_price.py       # SARIMAX price forecaster + seasonal fallback
│   │   ├── weather.py          # SARIMAX weather + XGBoost classifier
│   │   ├── crop_recommender.py # Random Forest + SHAP explainer
│   │   ├── irrigation.py       # Decision Tree irrigation advisor
│   │   └── anomaly.py          # Isolation Forest price anomaly detector
│   ├── models/                 # Pydantic MongoDB document schemas
│   ├── rag/
│   │   ├── embeddings.py       # FastEmbed singleton (BAAI/bge-small-en)
│   │   ├── qdrant_client.py    # Qdrant client singleton
│   │   ├── ingestor.py         # PDF/TXT → chunks → vectors → Qdrant
│   │   └── retriever.py        # Query → cosine search → top-k chunks
│   └── routers/                # FastAPI route handlers (8 routers)
├── frontend/
│   └── src/
│       ├── api/                # Axios clients per domain (auth, ml, agents...)
│       ├── hooks/              # useAutoTranslate, custom data hooks
│       ├── pages/              # 11 page components
│       ├── store/              # Zustand: authStore, agentStore
│       └── components/         # Shared UI components
├── research/
│   └── causal_price_analysis.py  # DoWhy causal inference: rainfall→yield→price
├── rag_data/
│   ├── crop_guides/            # ICAR cultivation guides (PDF/TXT)
│   └── pest_control/           # ICAR pest management documents (PDF/TXT)
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Local Qdrant container
├── render.yaml                 # Render IaC deployment config
├── requirements.txt            # Python dependencies
└── .github/workflows/          # GitHub Actions CI/CD pipeline
```

---

## Fields of AI/ML Covered

| Domain | Technique | Where Used |
|--------|-----------|------------|
| Time Series Forecasting | SARIMAX | Weather + crop price prediction |
| Supervised Classification | Random Forest, XGBoost, Decision Tree | Crop recommendation, weather condition, irrigation |
| Anomaly Detection | Isolation Forest | Price spike detection |
| Deep Learning / CNN | MobileNetV2 | Plant disease identification |
| Large Language Models | LLaMA-3.1-8b, LLaMA-3.3-70b | Weather/market/advisory/supervisor agents |
| Multi-Agent Systems | LangGraph StateGraph | Orchestrating 5 specialized AI agents |
| Retrieval-Augmented Generation | FastEmbed + Qdrant | Knowledge-grounded agricultural advice |
| Explainable AI (XAI) | SHAP (TreeExplainer) | Why the model recommended a specific crop |
| Causal Inference | DoWhy DAG + refutation tests | Rainfall → yield → price causal pathway |
| Natural Language Processing | i18next + Google Translate API | 7-language UI translation |
| Statistical Modelling | Multiplicative seasonal decomposition | Crop price estimation for 6 crops |

---

## License

MIT
