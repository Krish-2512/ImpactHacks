"""
WeatherTool — wraps the fetching + weather analysis agents.

Reads: farm_state, agent_timings (from state)
Writes: weather_forecast, weather_interpretation, planting_advice,
        irrigation_advice, weather_alerts, weather_confidence, agent_timings
"""
import time
from typing import Any
from backend.tools.base import BaseTool


class WeatherTool(BaseTool):
    name = "weather"
    description = (
        "Fetches real-time or model-based weather forecast for the farm location, "
        "then provides weather interpretation, planting advice, irrigation advice, "
        "and weather alerts specific to the farmer's crops."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "farm_state": {"type": "object", "description": "Farmer profile with location and primary_crops"},
        },
        "required": ["farm_state"],
    }

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        from backend.agents import fetching_agent, weather_agent

        # Run fetching agent (gets weather_forecast + crop_prices)
        state = await fetching_agent.run(state)
        # Run weather agent (interprets weather_forecast)
        state = await weather_agent.run(state)

        return {
            "weather_forecast":       state.get("weather_forecast", {}),
            "weather_interpretation": state.get("weather_interpretation", ""),
            "planting_advice":        state.get("planting_advice", ""),
            "irrigation_advice":      state.get("irrigation_advice", ""),
            "weather_alerts":         state.get("weather_alerts", []),
            "weather_confidence":     state.get("weather_confidence", 0.0),
            "agent_timings":          state.get("agent_timings", {}),
        }
