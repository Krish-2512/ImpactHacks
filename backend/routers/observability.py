"""
Observability router — query execution traces.

GET /observability/traces               → last N traces (summary)
GET /observability/traces/{cycle_id}    → full trace for a cycle
GET /observability/stats                → aggregate stats (latency, token usage, verdict distribution)
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from backend.auth.dependencies import get_current_user
from backend.database.mongodb import get_db

router = APIRouter()


def _serialize(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


@router.get("/traces")
async def list_traces(
    limit: int = Query(default=20, le=100),
    days: int = Query(default=7, le=90),
    _user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List recent execution traces (last N, within last `days` days)."""
    since = datetime.utcnow() - timedelta(days=days)
    cursor = db["execution_traces"].find(
        {"timestamp": {"$gte": since}},
        {
            "cycle_id": 1, "farmer_id": 1, "timestamp": 1, "intent": 1,
            "status": 1, "total_duration_ms": 1, "final_confidence": 1,
            "total_tokens_estimated": 1, "rag_sources_count": 1,
            "planner_decision.selected_tools": 1,
            "judge_output.verdict": 1,
        },
    ).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(limit)
    return [_serialize(d) for d in docs]


@router.get("/traces/{cycle_id}")
async def get_trace(
    cycle_id: str,
    _user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Full trace for a specific agent cycle."""
    doc = await db["execution_traces"].find_one({"cycle_id": cycle_id})
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Trace not found")
    return _serialize(doc)


@router.get("/stats")
async def observability_stats(
    days: int = Query(default=30, le=90),
    _user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Aggregate stats over the last `days` days."""
    since = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$group": {
            "_id": None,
            "total_cycles":         {"$sum": 1},
            "avg_duration_ms":      {"$avg": "$total_duration_ms"},
            "avg_tokens":           {"$avg": "$total_tokens_estimated"},
            "avg_confidence":       {"$avg": "$final_confidence"},
            "avg_rag_sources":      {"$avg": "$rag_sources_count"},
            "completed":            {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
            "failed":               {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
            "partial":              {"$sum": {"$cond": [{"$eq": ["$status", "partial"]}, 1, 0]}},
            "judge_pass":           {"$sum": {"$cond": [{"$eq": ["$judge_output.verdict", "pass"]}, 1, 0]}},
            "judge_flag":           {"$sum": {"$cond": [{"$eq": ["$judge_output.verdict", "flag"]}, 1, 0]}},
            "judge_reject":         {"$sum": {"$cond": [{"$eq": ["$judge_output.verdict", "reject"]}, 1, 0]}},
        }},
    ]

    cursor = db["execution_traces"].aggregate(pipeline)
    rows = await cursor.to_list(1)
    stats = rows[0] if rows else {}
    stats.pop("_id", None)

    # Tool frequency
    tool_pipeline = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$unwind": "$tool_traces"},
        {"$group": {
            "_id": "$tool_traces.tool",
            "count": {"$sum": 1},
            "avg_ms": {"$avg": "$tool_traces.duration_ms"},
            "avg_confidence": {"$avg": "$tool_traces.confidence"},
        }},
        {"$sort": {"count": -1}},
    ]
    tool_cursor = db["execution_traces"].aggregate(tool_pipeline)
    tool_stats = await tool_cursor.to_list(20)
    for t in tool_stats:
        t["tool"] = t.pop("_id")

    return {
        "period_days": days,
        "summary": stats,
        "tool_stats": tool_stats,
    }
