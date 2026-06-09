"""
Extra ML endpoints:
  POST /ml/recommend-crop    — Random Forest crop recommendation
  POST /ml/irrigation        — Decision Tree irrigation advice
  GET  /ml/price-anomaly     — Isolation Forest price anomaly detection
  GET  /ml/model-info        — Summary of all loaded ML models
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from backend.auth.dependencies import get_current_user
from backend.ml.model_cache import ModelCache

router = APIRouter(prefix="/ml", tags=["ml"])


# ── Crop Recommender ──────────────────────────────────────────────────────────

class CropRecommendRequest(BaseModel):
    N:           float = Field(..., ge=0,   le=200, description="Nitrogen content (kg/ha)")
    P:           float = Field(..., ge=0,   le=150, description="Phosphorous content (kg/ha)")
    K:           float = Field(..., ge=0,   le=200, description="Potassium content (kg/ha)")
    temperature: float = Field(..., ge=5,   le=45,  description="Average temperature (°C)")
    humidity:    float = Field(..., ge=10,  le=100, description="Relative humidity (%)")
    pH:          float = Field(..., ge=3.5, le=9.5, description="Soil pH")
    rainfall:    float = Field(..., ge=50,  le=4000, description="Annual rainfall (mm)")


@router.post("/recommend-crop")
async def recommend_crop(
    body: CropRecommendRequest,
    _user=Depends(get_current_user),
):
    import asyncio
    mc = ModelCache.get()
    try:
        kwargs = dict(
            N=body.N, P=body.P, K=body.K,
            temperature=body.temperature,
            humidity=body.humidity,
            pH=body.pH,
            rainfall=body.rainfall,
        )
        recommendations = mc.crop_recommender.predict(**kwargs, top_k=3)
        importance      = mc.crop_recommender.feature_importance()

        # SHAP is CPU-bound (tree traversal) — run in thread pool
        try:
            shap_explanation = await asyncio.to_thread(
                mc.crop_recommender.explain_prediction, **kwargs
            )
        except Exception as shap_err:
            shap_explanation = {"error": str(shap_err)}

        return {
            "recommendations":    recommendations,
            "feature_importance": importance,
            "shap_explanation":   shap_explanation,
            "input": body.model_dump(),
            "note": "Based on ICAR agronomic parameters for Northeast India",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crop recommendation failed: {e}")


# ── Irrigation Advisor ────────────────────────────────────────────────────────

class IrrigationRequest(BaseModel):
    crop:            str   = Field(..., description="Crop name (e.g. tomato, potato)")
    growth_stage:    str   = Field(..., description="seedling | vegetative | flowering | fruiting")
    days_since_rain: float = Field(..., ge=0, le=30,  description="Days since last rainfall")
    rain_this_week:  float = Field(..., ge=0, le=200, description="Rainfall this week (mm)")
    temperature:     float = Field(..., ge=5, le=45,  description="Current temperature (°C)")
    humidity:        float = Field(..., ge=5, le=100, description="Current humidity (%)")


@router.post("/irrigation")
async def irrigation_advice(
    body: IrrigationRequest,
    _user=Depends(get_current_user),
):
    mc = ModelCache.get()
    try:
        result = mc.irrigation_advisor.predict(
            crop=body.crop,
            growth_stage=body.growth_stage,
            days_since_rain=body.days_since_rain,
            rain_this_week=body.rain_this_week,
            temperature=body.temperature,
            humidity=body.humidity,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Irrigation prediction failed: {e}")


# ── Price Anomaly Detector ────────────────────────────────────────────────────

@router.get("/price-anomaly")
async def price_anomaly(_user=Depends(get_current_user)):
    from datetime import date

    mc = ModelCache.get()
    try:
        today_str = date.today().strftime("%d-%m-%Y")
        prices    = mc.crop_price.forecast(today_str)
        result    = mc.price_anomaly.detect(prices)
        result["date"] = date.today().strftime("%Y-%m-%d")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {e}")


# ── Model Info ────────────────────────────────────────────────────────────────

@router.get("/model-info")
async def model_info(_user=Depends(get_current_user)):
    return {
        "models": [
            {
                "name": "SARIMAX Weather Forecaster",
                "type": "Time Series (SARIMAX)",
                "task": "Predict Temperature, Humidity, Wind Speed, Precipitation",
                "variables": 4,
                "fallback_for": "Open-Meteo API (used when internet unavailable)",
            },
            {
                "name": "XGBoost Weather Classifier",
                "type": "Gradient Boosting Classifier",
                "task": "Classify weather condition (Sunny / Cloudy / Rainy / etc.)",
                "classes": 8,
            },
            {
                "name": "SARIMAX Crop Price Forecaster",
                "type": "Time Series (SARIMAX)",
                "task": "Forecast prices for brinjal, cabbage, lemon, tomato",
                "crops": 4,
            },
            {
                "name": "Seasonal Price Calculator",
                "type": "Deterministic Seasonal Model",
                "task": "Estimate prices for potato, onion, ginger, turmeric, chili, garlic",
                "crops": 6,
                "formula": "base_price × seasonal_multiplier[month] × (1 + 0.04 × sin(2π × doy/365))",
            },
            {
                "name": "Random Forest Crop Recommender",
                "type": "Ensemble Classifier (Random Forest, 200 trees)",
                "task": "Recommend best crop based on soil NPK, temperature, humidity, pH, rainfall",
                "crops": 10,
                "features": 7,
                "training_samples": 3500,
            },
            {
                "name": "Decision Tree Irrigation Advisor",
                "type": "Decision Tree (Classifier + Regressor)",
                "task": "Decide whether to irrigate and recommend water amount (mm)",
                "crops": 10,
                "stages": ["seedling", "vegetative", "flowering", "fruiting"],
            },
            {
                "name": "Isolation Forest Price Anomaly Detector",
                "type": "Anomaly Detection (Isolation Forest, 150 trees)",
                "task": "Detect unusual price movements across all 10 crops",
                "contamination": "5%",
                "training_days": 730,
            },
            {
                "name": "MobileNetV2 Plant Disease Detector",
                "type": "Convolutional Neural Network (MobileNetV2)",
                "task": "Identify plant diseases from leaf photographs",
                "classes": 38,
                "dataset": "PlantVillage",
                "source": "HuggingFace: linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification",
            },
        ],
        "total_models": 8,
        "ml_frameworks": ["scikit-learn", "statsmodels", "xgboost", "transformers", "torch"],
    }
