import time
from datetime import datetime
from backend.agents.state import AgentState
from backend.ml.model_cache import ModelCache
from backend.config import settings


async def run(state: AgentState) -> AgentState:
    """
    Data collection layer — no LLM.
    Tries live Open-Meteo weather first (if USE_LIVE_WEATHER=true),
    falls back to SARIMAX/seasonal model.
    """
    t0 = time.perf_counter()
    cache = ModelCache.get()

    today_weather = datetime.today().strftime('%Y-%m-%d')
    today_price   = datetime.today().strftime('%d-%m-%Y')

    # --- Weather: try live API first ---
    weather: dict = {}
    if getattr(settings, "USE_LIVE_WEATHER", False):
        try:
            from backend.integrations.weather_live import fetch_live_weather
            weather = await fetch_live_weather(settings.WEATHER_LAT, settings.WEATHER_LON)
            weather["_source"] = "live"
        except Exception as e:
            print(f"[fetching_agent] Live weather failed ({e}), using ML model")

    if not weather:
        weather = cache.weather.forecast(today_weather)
        weather["_source"] = "sarimax" if getattr(cache.weather, "_using_sarimax", False) else "fallback"

    condition = cache.weather_classifier.predict(weather)
    weather["Condition"] = condition

    # --- Crop prices ---
    prices = cache.crop_price.forecast(today_price)

    elapsed = (time.perf_counter() - t0) * 1000
    timings = {**state.get("agent_timings", {}), "fetching": round(elapsed, 1)}

    return {
        **state,
        "weather_forecast": weather,
        "crop_prices": prices,
        "agent_timings": timings,
    }
