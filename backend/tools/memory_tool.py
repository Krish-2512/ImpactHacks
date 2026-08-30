"""
MemoryTool — retrieves and summarizes farmer's historical memory.

Reads: farmer_id, farm_state (for intent-based semantic query)
Writes: memory_context, selected_memories, memory_retrieval_query
"""
from typing import Any
from backend.tools.base import BaseTool


class MemoryTool(BaseTool):
    name = "memory"
    description = (
        "Retrieves the farmer's historical farming cycles from long-term memory. "
        "Performs semantic search to find past experiences relevant to the current "
        "season, weather, or crop situation. Provides personalized context to all agents."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "farmer_id": {"type": "string"},
            "farm_state": {"type": "object", "description": "Used to build memory retrieval query"},
        },
        "required": ["farmer_id"],
    }

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        from backend.memory.memory_manager import get_recent_memories
        from backend.memory.summarizer import summarize_memories

        farmer_id = state.get("farmer_id", "")
        if not farmer_id:
            return {"memory_context": "", "selected_memories": [], "memory_retrieval_query": ""}

        # Build retrieval query from current context
        farm_state = state.get("farm_state", {})
        crops = ", ".join(farm_state.get("primary_crops", []))
        weather_cond = state.get("weather_forecast", {}).get("Condition", "")
        retrieval_query = f"{crops} farming {weather_cond} Northeast India seasonal advice".strip()

        # Try semantic retrieval first, fall back to recency
        memories = []
        try:
            from backend.memory.memory_vectorstore import get_relevant_memories
            memories = await get_relevant_memories(farmer_id, retrieval_query, k=8)
        except Exception:
            pass

        if not memories:
            memories = await get_recent_memories(farmer_id, limit=15)

        memory_context = ""
        if memories:
            memory_context = await summarize_memories(memories)

        return {
            "memory_context":        memory_context,
            "selected_memories":     memories,
            "memory_retrieval_query": retrieval_query,
        }
