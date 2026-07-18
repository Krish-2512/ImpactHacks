"""
SchemeTool — retrieves government agricultural scheme information via RAG.

Searches the knowledge base for documents tagged "schemes" or "government".
Returns relevant scheme info the farmer may benefit from.

Reads: farm_state, sell_hold_decisions
Writes: scheme_info (list of relevant scheme summaries with sources)
"""
from typing import Any
from backend.tools.base import BaseTool


class SchemeTool(BaseTool):
    name = "schemes"
    description = (
        "Searches the knowledge base for government agricultural schemes, subsidies, "
        "insurance programs (like PMFBY), and support services relevant to the farmer's "
        "crops, location, and current situation."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "farm_state": {"type": "object", "description": "Farmer profile with crops and location"},
        },
    }

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        farm_state = state.get("farm_state", {})
        crops = ", ".join(farm_state.get("primary_crops", []))
        location = farm_state.get("location", "Northeast India")

        query = f"government scheme subsidy insurance {crops} farmer {location}"

        try:
            from backend.rag.retriever import retrieve_context_with_sources
            import asyncio

            results = await asyncio.to_thread(
                retrieve_context_with_sources,
                query,
                top_k=4,
                score_threshold=0.25,
            )
        except Exception:
            results = []

        return {
            "scheme_info": [
                {
                    "text":   r.get("text", ""),
                    "source": r.get("source", ""),
                    "score":  r.get("score", 0.0),
                }
                for r in results
            ]
        }
