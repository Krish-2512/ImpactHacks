"""
ExecutionTracer — records planner decisions, tool calls, timing, token estimates,
and judge verdicts into MongoDB `execution_traces`.

Usage in agents.py:
    tracer = ExecutionTracer(cycle_id, farmer_id)
    # after pipeline completes:
    await tracer.finalize(result_state, db)
"""
import logging
import time
from datetime import datetime
from typing import Any

from backend.observability.models import ExecutionTrace, ToolTrace
from backend.context.token_counter import count_tokens

logger = logging.getLogger(__name__)


class ExecutionTracer:

    def __init__(self, cycle_id: str, farmer_id: str) -> None:
        self._trace = ExecutionTrace(cycle_id=cycle_id, farmer_id=farmer_id)
        self._pipeline_start = time.perf_counter()

    def record_planner(self, planner_decision: dict[str, Any], intent: str) -> None:
        self._trace.intent = intent
        self._trace.planner_decision = planner_decision

    def record_tool(
        self,
        tool: str,
        duration_ms: float,
        confidence: float = 0.0,
        input_text: str = "",
        output_text: str = "",
        error: str | None = None,
    ) -> None:
        tt = ToolTrace(
            tool=tool,
            started_at=time.perf_counter(),
            duration_ms=duration_ms,
            input_tokens_est=count_tokens(input_text),
            output_tokens_est=count_tokens(output_text),
            confidence=confidence,
            error=error,
            input_summary=input_text[:200],
            output_summary=output_text[:200],
        )
        self._trace.tool_traces.append(tt)

    def finalize_from_state(self, result: dict[str, Any]) -> None:
        """Populate summary fields from the completed AgentState."""
        timings = result.get("agent_timings", {})
        total_ms = sum(timings.values())
        self._trace.total_duration_ms = round(total_ms, 1)

        # Tool-level traces from timings (simplified — detailed traces added via record_tool)
        existing_tools = {t.tool for t in self._trace.tool_traces}
        for tool_name, ms in timings.items():
            if tool_name not in existing_tools:
                conf = result.get(f"{tool_name}_confidence", 0.0)
                self._trace.tool_traces.append(ToolTrace(
                    tool=tool_name,
                    started_at=0,
                    duration_ms=ms,
                    confidence=conf,
                ))

        # Estimate total tokens (all LLM inputs + outputs)
        all_text = (
            result.get("final_report", "")
            + result.get("crop_advisory", "")
            + result.get("market_analysis", "")
            + result.get("weather_interpretation", "")
        )
        self._trace.total_tokens_estimated = count_tokens(all_text) * 3   # rough in+out estimate

        self._trace.rag_sources_count = len(result.get("rag_sources", []))
        self._trace.memory_entries_used = len(result.get("selected_memories", []))
        self._trace.final_confidence = result.get("supervisor_confidence", 0.0)
        self._trace.judge_output = result.get("judge_output", {})
        self._trace.planner_decision = result.get("planner_decision", self._trace.planner_decision)
        self._trace.intent = result.get("intent", self._trace.intent)

        verdict = result.get("judge_output", {}).get("verdict", "pass")
        self._trace.status = "partial" if verdict == "reject" else "completed"

    async def save(self, db) -> None:
        """Write trace to MongoDB. Always called in a finally block."""
        try:
            doc = self._trace.to_dict()
            await db["execution_traces"].update_one(
                {"cycle_id": self._trace.cycle_id},
                {"$set": doc},
                upsert=True,
            )
            logger.debug("Trace saved for cycle %s", self._trace.cycle_id)
        except Exception as e:
            logger.warning("Trace save failed: %s", e)

    async def mark_failed(self, db, error: str) -> None:
        self._trace.status = "failed"
        self._trace.total_duration_ms = round(
            (time.perf_counter() - self._pipeline_start) * 1000, 1
        )
        await self.save(db)
