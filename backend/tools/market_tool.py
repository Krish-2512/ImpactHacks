"""
MarketTool — wraps the market analysis agent.

Reads: crop_prices, weather_forecast, farm_state, agent_timings (from state)
Writes: market_analysis, sell_hold_decisions, price_alerts, best_selling_window,
        market_confidence, agent_timings, crop_prices (if fetching not yet done)
"""
from typing import Any
from backend.tools.base import BaseTool


class MarketTool(BaseTool):
    name = "market"
    description = (
        "Fetches current crop price forecasts and performs market analysis. "
        "Provides SELL/HOLD/WAIT decisions per crop, price alerts, "
        "and the best selling window considering current weather impact on prices."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "crop_prices":     {"type": "object", "description": "Crop price dict (INR/quintal)"},
            "weather_forecast": {"type": "object", "description": "Current weather for price context"},
        },
    }

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        from backend.agents import fetching_agent, market_agent

        # Ensure crop_prices are fetched (if weather_tool didn't run first)
        if not state.get("crop_prices"):
            state = await fetching_agent.run(state)

        state = await market_agent.run(state)

        return {
            "crop_prices":         state.get("crop_prices", {}),
            "market_analysis":     state.get("market_analysis", ""),
            "sell_hold_decisions": state.get("sell_hold_decisions", {}),
            "price_alerts":        state.get("price_alerts", []),
            "best_selling_window": state.get("best_selling_window", ""),
            "market_confidence":   state.get("market_confidence", 0.0),
            "agent_timings":       state.get("agent_timings", {}),
        }
