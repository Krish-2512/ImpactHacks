"""
Observability data models — stored in MongoDB `execution_traces` collection.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass
class ToolTrace:
    tool: str
    started_at: float          # perf_counter timestamp
    duration_ms: float = 0.0
    input_tokens_est: int = 0
    output_tokens_est: int = 0
    confidence: float = 0.0
    error: str | None = None
    input_summary: str = ""    # first 200 chars of context sent to tool
    output_summary: str = ""   # first 200 chars of tool output


@dataclass
class ExecutionTrace:
    cycle_id: str
    farmer_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    intent: str = ""
    planner_decision: dict[str, Any] = field(default_factory=dict)
    tool_traces: list[ToolTrace] = field(default_factory=list)
    judge_output: dict[str, Any] = field(default_factory=dict)
    rag_sources_count: int = 0
    memory_entries_used: int = 0
    total_duration_ms: float = 0.0
    total_tokens_estimated: int = 0
    final_confidence: float = 0.0
    status: str = "running"    # running | completed | partial | failed

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tool_traces"] = [asdict(t) for t in self.tool_traces]
        return d
