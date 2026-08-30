from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime, timedelta
from backend.ml.model_cache import ModelCache
from backend.auth.dependencies import get_current_user
from backend.integrations.weather_api import fetch_weather_forecast

router = APIRouter()


@router.get("/weather")
async def get_weather_forecast(_user=Depends(get_current_user)):
    """
    Real-time 7-day weather from Open-Meteo (free, no API key).
    Falls back to SARIMAX ML model if the API is unreachable.
    """
    try:
        return await fetch_weather_forecast()
    except Exception as api_err:
        print(f"[WARNING] Open-Meteo API failed ({api_err}), falling back to SARIMAX")
        # Fallback: SARIMAX model (may be inaccurate far from training cutoff)
        cache = ModelCache.get()
        today = datetime.today()
        forecast_7d = []
        for i in range(7):
            day = today + timedelta(days=i)
            date_str = day.strftime('%Y-%m-%d')
            data = cache.weather.forecast(date_str)
            condition = cache.weather_classifier.predict(data)
            forecast_7d.append({
                **data,
                "Condition": condition,
                "date": date_str,
                "label": "Today" if i == 0 else day.strftime("%a %d"),
                "source": "sarimax-fallback",
            })
        return {"today": forecast_7d[0], "forecast": forecast_7d}


@router.get("/prices")
async def get_crop_prices(_user=Depends(get_current_user)):
    """Today's prices for all 10 crops."""
    cache = ModelCache.get()
    today = datetime.today().strftime('%d-%m-%Y')
    prices = cache.crop_price.forecast(today)
    return {"prices": prices, "date": today, "unit": "INR/quintal"}


@router.get("/prices/forecast")
async def get_price_forecast(
    days: int = Query(default=10, ge=1, le=30),
    _user=Depends(get_current_user),
):
    """Price forecast for the next N days (used for the chart)."""
    cache = ModelCache.get()
    today = datetime.today()
    result = []
    for i in range(days):
        day = today + timedelta(days=i)
        date_str = day.strftime('%d-%m-%Y')
        prices = cache.crop_price.forecast(date_str)
        result.append({
            "date": day.strftime('%Y-%m-%d'),
            "label": "Today" if i == 0 else day.strftime("%a %d"),
            **prices,
        })
    return {"forecast": result, "unit": "INR/quintal"}
