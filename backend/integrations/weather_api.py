"""
Open-Meteo weather integration — free, no API key required.
Docs: https://open-meteo.com/en/docs
Default location: Guwahati, Assam (26.1445°N, 91.7362°E)
"""
import httpx
from datetime import datetime
from backend.config import settings

# WMO weather interpretation codes → human-readable condition
WMO_CONDITION = {
    0: "Clear Sky",
    1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy Fog",
    51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Heavy Drizzle",
    61: "Light Rain", 63: "Moderate Rain", 65: "Heavy Rain",
    71: "Light Snow", 73: "Moderate Snow", 75: "Heavy Snow",
    80: "Rain Showers", 81: "Moderate Showers", 82: "Heavy Showers",
    95: "Thunderstorm", 96: "Thunderstorm with Hail", 99: "Heavy Thunderstorm",
}


def _wmo_to_condition(code: int) -> str:
    return WMO_CONDITION.get(code, "Partly Cloudy")


async def fetch_weather_forecast() -> dict:
    """
    Returns {today: {...}, forecast: [{...} x7]} using real Open-Meteo data.
    Fields match the format the rest of the app expects:
      Temperature, Humidity, Wind_Speed, Precipitation, Condition, date, label
    """
    lat = getattr(settings, "WEATHER_LAT", 26.1445)
    lon = getattr(settings, "WEATHER_LON", 91.7362)

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weathercode"
        f"&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum,"
        f"wind_speed_10m_max,relative_humidity_2m_max"
        f"&forecast_days=7"
        f"&timezone=Asia%2FKolkata"
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    current = data["current"]
    daily   = data["daily"]

    today_entry = {
        "Temperature":   round(current["temperature_2m"], 1),
        "Humidity":      round(current["relative_humidity_2m"], 1),
        "Wind_Speed":    round(current["wind_speed_10m"], 1),
        "Precipitation": round(current["precipitation"], 1),
        "Condition":     _wmo_to_condition(current["weathercode"]),
        "date":          daily["time"][0],
        "label":         "Today",
        "source":        "open-meteo",
    }

    forecast = []
    for i, date_str in enumerate(daily["time"]):
        day = datetime.strptime(date_str, "%Y-%m-%d")
        # Daily averages: use midpoint of max/min for temperature, max for others
        temp_max = daily["temperature_2m_max"][i]
        temp_min = daily["temperature_2m_min"][i]
        forecast.append({
            "Temperature":   round((temp_max + temp_min) / 2, 1),
            "Humidity":      round(daily["relative_humidity_2m_max"][i], 1),
            "Wind_Speed":    round(daily["wind_speed_10m_max"][i], 1),
            "Precipitation": round(daily["precipitation_sum"][i], 1),
            "Condition":     _wmo_to_condition(daily["weathercode"][i]),
            "date":          date_str,
            "label":         "Today" if i == 0 else day.strftime("%a %d"),
            "temp_max":      round(temp_max, 1),
            "temp_min":      round(temp_min, 1),
            "source":        "open-meteo",
        })

    return {"today": today_entry, "forecast": forecast}
