"""
Tool registry — single source of truth for all available tools.

The planner agent reads TOOL_REGISTRY to know what tools exist and their descriptions.
New tools: subclass BaseTool and add an instance here.
"""
from backend.tools.weather_tool import WeatherTool
from backend.tools.market_tool import MarketTool
from backend.tools.rag_tool import RAGTool
from backend.tools.disease_tool import DiseaseTool
from backend.tools.memory_tool import MemoryTool
from backend.tools.scheme_tool import SchemeTool
from backend.tools.multimodal_tool import MultimodalAdvisoryTool

_all_tools = [
    WeatherTool(),
    MarketTool(),
    RAGTool(),
    DiseaseTool(),
    MemoryTool(),
    SchemeTool(),
    MultimodalAdvisoryTool(),
]

TOOL_REGISTRY: dict[str, "BaseTool"] = {t.name: t for t in _all_tools}  # noqa: F821

# Planner-visible tool descriptions (name + description pairs)
TOOL_DESCRIPTIONS: str = "\n".join(t.to_planner_description() for t in _all_tools)

__all__ = ["TOOL_REGISTRY", "TOOL_DESCRIPTIONS"]
