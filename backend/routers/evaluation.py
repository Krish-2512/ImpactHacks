"""
Evaluation router — RAGAS-style quality metrics for completed agent cycles.

GET  /evaluation/dashboard              → aggregated metrics (last 30 cycles)
POST /evaluation/run/{cycle_id}         → evaluate a specific completed cycle on-demand
GET  /evaluation/results/{cycle_id}     → fetch stored evaluation result for a cycle
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from backend.auth.dependencies import get_current_user
from backend.database.mongodb import get_db
from backend.evaluation.evaluator import EvaluationRunner

logger = logging.getLogger(__name__)
router = APIRouter()


def _clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


@router.post("/run/{cycle_id}", summary="Evaluate a completed cycle on demand")
async def run_evaluation(
    cycle_id: str,
    _user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Triggers evaluation for a specific cycle and stores results. Returns the result immediately."""
    cycle = await db["agent_cycles"].find_one({"cycle_id": cycle_id})
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    if cycle.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"Cycle status is '{cycle.get('status')}'; evaluation requires completed cycles")

    cycle["_id"] = str(cycle["_id"])
    result = await EvaluationRunner.evaluate_and_save(cycle, db)
    return _clean(result)


@router.get("/results/{cycle_id}", summary="Get stored evaluation result for a cycle")
async def get_evaluation_result(
    cycle_id: str,
    _user=Depends(get_current_user),
    db=Depends(get_db),
):
    doc = await db["evaluation_results"].find_one({"cycle_id": cycle_id})
    if not doc:
        raise HTTPException(status_code=404, detail="No evaluation found for this cycle. POST /evaluation/run/{cycle_id} first.")
    return _clean(doc)


@router.get("/dashboard", summary="Aggregated evaluation metrics over last N cycles")
async def evaluation_dashboard(
    days: int = Query(default=30, le=90),
    limit: int = Query(default=30, le=100),
    _user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Returns aggregate stats + per-cycle breakdown for the evaluation dashboard."""
    since = datetime.utcnow() - timedelta(days=days)

    # Aggregate stats
    agg_pipeline = [
        {"$match": {"timestamp": {"$gte": since}, "error": None}},
        {"$group": {
            "_id": None,
            "total_evaluated":      {"$sum": 1},
            "avg_faithfulness":     {"$avg": "$faithfulness"},
            "avg_answer_relevance": {"$avg": "$answer_relevance"},
            "avg_context_precision":{"$avg": "$context_precision"},
            "avg_latency_ms":       {"$avg": "$latency_ms"},
            "avg_confidence":       {"$avg": "$supervisor_confidence"},
            "avg_rag_sources":      {"$avg": "$rag_sources_count"},
            "judge_pass":           {"$sum": {"$cond": [{"$eq": ["$judge_verdict", "pass"]}, 1, 0]}},
            "judge_flag":           {"$sum": {"$cond": [{"$eq": ["$judge_verdict", "flag"]}, 1, 0]}},
            "judge_reject":         {"$sum": {"$cond": [{"$eq": ["$judge_verdict", "reject"]}, 1, 0]}},
        }},
    ]
    cursor = db["evaluation_results"].aggregate(agg_pipeline)
    rows = await cursor.to_list(1)
    summary = rows[0] if rows else {}
    summary.pop("_id", None)

    # Round floats for cleaner output
    for key in ("avg_faithfulness", "avg_answer_relevance", "avg_context_precision",
                "avg_latency_ms", "avg_confidence", "avg_rag_sources"):
        if key in summary:
            summary[key] = round(summary[key], 4)

    # Latency percentiles from execution_traces (p50/p95/p99)
    latency_pipeline = [
        {"$match": {"timestamp": {"$gte": since}, "status": "completed"}},
        {"$group": {"_id": None, "latencies": {"$push": "$total_duration_ms"}}},
    ]
    lt_cursor = db["execution_traces"].aggregate(latency_pipeline)
    lt_rows = await lt_cursor.to_list(1)
    latency_percentiles = {}
    if lt_rows and lt_rows[0].get("latencies"):
        lats = sorted(lt_rows[0]["latencies"])
        n = len(lats)
        latency_percentiles = {
            "p50": lats[int(n * 0.50)],
            "p95": lats[int(n * 0.95)],
            "p99": lats[min(int(n * 0.99), n - 1)],
            "count": n,
        }

    # Per-cycle results (most recent first)
    recent = await db["evaluation_results"].find(
        {"timestamp": {"$gte": since}},
        {"cycle_id": 1, "timestamp": 1, "faithfulness": 1, "answer_relevance": 1,
         "context_precision": 1, "latency_ms": 1, "supervisor_confidence": 1,
         "judge_verdict": 1, "rag_sources_count": 1},
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    for r in recent:
        r.pop("_id", None)

    return {
        "period_days": days,
        "summary": summary,
        "latency_percentiles": latency_percentiles,
        "recent_cycles": recent,
    }
