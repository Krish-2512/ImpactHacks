"""
Dynamic multi-agent graph.

Execution order:
  fetching → memory → planner → [tool fan-out per planner_decision] → judge → supervisor → END

The planner's `parallel_groups` drives which tool-agents run.
Tools in the same group run via an async dispatcher node ("dispatch_N").
If planner fails, all default tools run sequentially (backward-compatible fallback).
"""
import asyncio
import logging
from typing import Any

from langgraph.graph import StateGraph, END
from backend.agents.state import AgentState
from backend.agents import fetching_agent, supervisor_agent

logger = logging.getLogger(__name__)


# ── Tool dispatcher ───────────────────────────────────────────────────────────

async def _run_tool(tool_name: str, state: dict[str, Any]) -> dict[str, Any]:
    """Run a single named tool and merge its output into a copy of state."""
    from backend.tools import TOOL_REGISTRY
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        logger.warning("Tool '%s' not found in registry — skipping", tool_name)
        return {}
    try:
        return await tool.run(state)
    except Exception as e:
        logger.error("Tool '%s' failed: %s", tool_name, e)
        return {"error": str(e)}


async def _dispatch_parallel_group(group: list[str], state: dict[str, Any]) -> dict[str, Any]:
    """Run all tools in a parallel group concurrently; merge results left-to-right."""
    results = await asyncio.gather(*[_run_tool(t, state) for t in group], return_exceptions=True)
    merged: dict[str, Any] = {}
    for r in results:
        if isinstance(r, dict):
            merged.update(r)
    return merged


# ── Graph node functions ──────────────────────────────────────────────────────

async def memory_node(state: dict[str, Any]) -> dict[str, Any]:
    """Load and summarize farmer memory (always runs before planner)."""
    from backend.tools import TOOL_REGISTRY
    memory_tool = TOOL_REGISTRY.get("memory")
    if not memory_tool:
        return {}
    try:
        return await memory_tool.run(state)
    except Exception as e:
        logger.warning("Memory node failed: %s", e)
        return {}


async def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    from backend.agents import planner_agent
    return await planner_agent.run(state)


async def tool_execution_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Execute all tools selected by the planner, respecting parallel_groups.
    Each group runs concurrently; groups run sequentially (dependency order).
    State is merged incrementally so later groups see earlier groups' outputs.
    """
    decision = state.get("planner_decision", {})
    parallel_groups: list[list[str]] = decision.get("parallel_groups", [])

    if not parallel_groups:
        # Fallback: run default tools sequentially
        parallel_groups = [["weather", "market"], ["advisory"]]

    current_state = dict(state)
    merged: dict[str, Any] = {}

    for group in parallel_groups:
        group_result = await _dispatch_parallel_group(group, current_state)
        merged.update(group_result)
        current_state.update(group_result)   # make outputs visible to next group

    return merged


async def judge_node(state: dict[str, Any]) -> dict[str, Any]:
    from backend.agents import judge_agent
    return await judge_agent.run(state)


# ── Graph construction ────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)

    # Always-on data collection
    graph.add_node("fetching",    fetching_agent.run)
    graph.add_node("memory",      memory_node)

    # Planning
    graph.add_node("planner",     planner_node)

    # Dynamic tool execution (fan-out handled inside the node)
    graph.add_node("tools",       tool_execution_node)

    # Quality gate
    graph.add_node("judge",       judge_node)

    # Final synthesis
    graph.add_node("supervisor",  supervisor_agent.run)

    # Edges
    graph.set_entry_point("fetching")
    graph.add_edge("fetching",  "memory")
    graph.add_edge("memory",    "planner")
    graph.add_edge("planner",   "tools")
    graph.add_edge("tools",     "judge")
    graph.add_edge("judge",     "supervisor")
    graph.add_edge("supervisor", END)

    return graph.compile()


agent_graph = build_graph()
