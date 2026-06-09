from datetime import datetime
from backend.agents.state import AgentState
from backend.ml.model_cache import ModelCache


async def run(state: AgentState) -> AgentState:
    """
    Collects all raw data: SARIMAX weather forecast, SARIMAX crop prices.
    No LLM call — pure data collection layer.
    """
    cache = ModelCache.get()

    today_weather = datetime.today().strftime('%Y-%m-%d')
    today_price = datetime.today().strftime('%d-%m-%Y')

    weather = cache.weather.forecast(today_weather)
    condition = cache.weather_classifier.predict(weather)
    weather["Condition"] = condition

    prices = cache.crop_price.forecast(today_price)

    return {
        **state,
        "weather_forecast": weather,
        "crop_prices": prices,
    }
