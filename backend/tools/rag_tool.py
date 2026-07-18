"""
RAGTool — wraps the advisory agent (RAG retrieval + crop advisory).

Reads: farm_state, weather_forecast, sell_hold_decisions, agent_timings (from state)
Writes: rag_query, rag_sources, crop_advisory, pest_warnings, advisory_confidence, agent_timings
"""
from typing import Any
from backend.tools.base import BaseTool


class RAGTool(BaseTool):
    name = "advisory"
    description = (
        "Retrieves relevant agricultural knowledge using hybrid RAG and produces "
        "crop-specific cultivation advice, pest/disease warnings, and treatment "
        "recommendations grounded in source documents with citations."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "farm_state":         {"type": "object", "description": "Farmer profile with primary_crops"},
            "weather_forecast":   {"type": "object", "description": "Weather context for disease risk"},
            "sell_hold_decisions": {"type": "object", "description": "Market decisions for harvest timing"},
        },
    }

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        from backend.agents import advisory_agent

        state = await advisory_agent.run(state)

        return {
            "rag_query":          state.get("rag_query", ""),
            "rag_sources":        state.get("rag_sources", []),
            "crop_advisory":      state.get("crop_advisory", ""),
            "pest_warnings":      state.get("pest_warnings", []),
            "advisory_confidence": state.get("advisory_confidence", 0.0),
            "agent_timings":      state.get("agent_timings", {}),
        }
