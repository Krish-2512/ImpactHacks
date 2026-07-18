"""
PlannerAgent — reads the farmer's intent and farm state, then selects which tools to invoke.

The planner uses GROQ_MODEL_FAST (temperature=0.1) for deterministic, low-latency decisions.
It outputs a structured JSON decision that the graph router uses to fan-out to only the
required tool-agents.

Default fallback: if the planner fails or returns an empty plan, all tools run (current behavior).
"""
import json
import logging
import time
from typing import Any

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import settings
from backend.tools import TOOL_DESCRIPTIONS

logger = logging.getLogger(__name__)

# Tools the planner can always choose from
PLANNABLE_TOOLS = ["weather", "market", "advisory", "disease", "schemes"]
DEFAULT_TOOLS   = ["weather", "market", "advisory"]     # fallback if planner fails

_SYSTEM_PROMPT = f"""You are an agricultural AI planner. Given a farmer's profile and context,
select ONLY the tools needed to answer their current situation.

Available tools:
{TOOL_DESCRIPTIONS}

Rules:
- Always include "weather" and "market" for general daily analysis.
- Include "advisory" when crop cultivation, pest, or disease knowledge is needed.
- Include "disease" ONLY if an image has been provided or pest/disease is suspected.
- Include "schemes" only if the farmer seems to need government support info.
- "memory" is always run automatically — do NOT include it in selected_tools.

Return ONLY valid JSON — no markdown, no explanation:
{{
  "intent": "<one of: full_analysis | market_only | weather_only | advisory_only | disease_focus | custom>",
  "selected_tools": ["weather", "market", "advisory"],
  "reasoning": "<one sentence>",
  "parallel_groups": [["weather", "market"], ["advisory"]]
}}

parallel_groups: group tools that can run concurrently (no data dependency between them).
"""


async def run(state: dict[str, Any]) -> dict[str, Any]:
    t0 = time.perf_counter()

    farm_state = state.get("farm_state", {})
    crops = ", ".join(farm_state.get("primary_crops", [])) or "general crops"
    location = farm_state.get("location", "Northeast India")
    has_image = bool(state.get("disease_image_b64"))

    user_msg = (
        f"Farmer location: {location}\n"
        f"Primary crops: {crops}\n"
        f"Image provided: {'Yes — run disease tool' if has_image else 'No'}\n"
        f"Memory context available: {'Yes' if state.get('memory_context') else 'No'}\n"
        f"Current weather condition: {state.get('weather_forecast', {}).get('Condition', 'Unknown')}\n"
        "Select the appropriate tools for today's farm intelligence cycle."
    )

    try:
        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL_FAST,
            temperature=0.1,
            max_tokens=300,
        )
        response = await llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])

        raw = response.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        decision = json.loads(raw.strip())

        # Validate & sanitize
        selected = [t for t in decision.get("selected_tools", []) if t in PLANNABLE_TOOLS]
        if not selected:
            selected = DEFAULT_TOOLS

        # Force disease tool if image provided
        if has_image and "disease" not in selected:
            selected.append("disease")

        parallel_groups = decision.get("parallel_groups", [selected])
        # Validate parallel_groups contains only selected tools
        parallel_groups = [
            [t for t in grp if t in selected]
            for grp in parallel_groups
        ]
        parallel_groups = [g for g in parallel_groups if g]
        if not parallel_groups:
            parallel_groups = [selected]

        planner_decision = {
            "selected_tools":  selected,
            "intent":          decision.get("intent", "full_analysis"),
            "reasoning":       decision.get("reasoning", ""),
            "parallel_groups": parallel_groups,
        }

    except Exception as e:
        logger.warning("Planner failed (%s) — using default tools: %s", type(e).__name__, e)
        planner_decision = {
            "selected_tools":  DEFAULT_TOOLS + (["disease"] if has_image else []),
            "intent":          "full_analysis",
            "reasoning":       "Planner failed — using default tool set.",
            "parallel_groups": [["weather", "market"], ["advisory"]],
        }

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    logger.info(
        "Planner [%s ms]: intent=%s tools=%s",
        elapsed_ms,
        planner_decision["intent"],
        planner_decision["selected_tools"],
    )

    return {
        "planner_decision": planner_decision,
        "intent":           planner_decision["intent"],
        "agent_timings":    {**state.get("agent_timings", {}), "planner": elapsed_ms},
    }
