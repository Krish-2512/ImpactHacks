"""
EvaluationRunner — runs RAGAS-style metrics on a completed agent cycle.

Stores results in MongoDB `evaluation_results` collection:
{
  cycle_id, farmer_id, timestamp,
  faithfulness, unsupported_claims,
  answer_relevance,
  context_precision, relevant_count, total_count,
  rag_sources_count, rag_query,
  latency_ms,
  supervisor_confidence, judge_verdict,
  error: str | None
}
"""
import asyncio
import logging
from datetime import datetime
from typing import Any

from backend.evaluation.metrics import faithfulness, answer_relevance, context_precision

logger = logging.getLogger(__name__)


class EvaluationRunner:

    def __init__(self, cycle_doc: dict[str, Any]) -> None:
        self._cycle = cycle_doc

    async def run(self) -> dict[str, Any]:
        """Execute all metrics concurrently and return a result dict."""
        cycle = self._cycle
        final_report = cycle.get("final_report", "")
        rag_sources = cycle.get("rag_sources", [])
        rag_query = cycle.get("agents_output", [{}])  # fallback

        # Best-effort extraction of rag_query from stored state
        _rag_query = ""
        for entry in cycle.get("agents_output", []):
            if entry.get("agent_name") == "AdvisoryAgent":
                _rag_query = entry.get("input_summary", "")
                break
        if not _rag_query:
            _rag_query = cycle.get("intent", "general crop advisory")

        latency_ms = 0.0
        timings = cycle.get("agent_timings", {})
        if timings:
            latency_ms = sum(timings.values())

        try:
            faith_res, relevance_res, precision_res = await asyncio.gather(
                faithfulness(final_report, rag_sources),
                answer_relevance(final_report, _rag_query),
                context_precision(_rag_query, rag_sources),
                return_exceptions=True,
            )
        except Exception as e:
            logger.warning("Evaluation gather failed: %s", e)
            faith_res = relevance_res = precision_res = {}

        def _safe(res, key, default=0.0):
            if isinstance(res, Exception):
                return default
            return res.get(key, default) if isinstance(res, dict) else default

        result = {
            "cycle_id": cycle.get("cycle_id", ""),
            "farmer_id": str(cycle.get("user_id", "")),
            "timestamp": datetime.utcnow(),
            "faithfulness": _safe(faith_res, "faithfulness"),
            "unsupported_claims": _safe(faith_res, "unsupported_claims", []),
            "answer_relevance": _safe(relevance_res, "answer_relevance"),
            "context_precision": _safe(precision_res, "context_precision"),
            "relevant_count": _safe(precision_res, "relevant_count", 0),
            "total_count": _safe(precision_res, "total_count", 0),
            "rag_sources_count": len(rag_sources),
            "rag_query": _rag_query,
            "latency_ms": round(latency_ms, 1),
            "supervisor_confidence": cycle.get("confidences", {}).get("supervisor", 0.0),
            "judge_verdict": cycle.get("judge_output", {}).get("verdict", "pass"),
            "error": None,
        }
        return result

    @classmethod
    async def evaluate_and_save(cls, cycle_doc: dict[str, Any], db) -> dict[str, Any]:
        runner = cls(cycle_doc)
        try:
            result = await runner.run()
        except Exception as e:
            logger.warning("Evaluation failed for cycle %s: %s", cycle_doc.get("cycle_id"), e)
            result = {
                "cycle_id": cycle_doc.get("cycle_id", ""),
                "farmer_id": str(cycle_doc.get("user_id", "")),
                "timestamp": datetime.utcnow(),
                "error": str(e),
            }

        await db["evaluation_results"].update_one(
            {"cycle_id": result["cycle_id"]},
            {"$set": result},
            upsert=True,
        )
        return result
