"""
Thin wrapper used by fetching_agent to get a flat weather dict
from the real Open-Meteo API (backend/integrations/weather_api.py).
"""
from backend.integrations.weather_api import fetch_weather_forecast


async def fetch_live_weather(lat: float, lon: float) -> dict:
    """
    Returns a flat dict matching the format expected by fetching_agent:
    {Temperature, Humidity, Wind_Speed, Precipitation, Condition, ...}
    """
    result = await fetch_weather_forecast()
    today = result["today"]
    today["_source"] = "live"
    return today
