import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.auth.dependencies import get_current_user
from backend.database.mongodb import get_db
from backend.agents.state import AgentState

router = APIRouter()


class RunCycleRequest(BaseModel):
    image_base64: Optional[str] = None

# --- SSE event registry ---
# Maps cycle_id → asyncio.Queue for real-time streaming
_sse_queues: dict[str, asyncio.Queue] = {}


def _get_queue(cycle_id: str) -> asyncio.Queue:
    if cycle_id not in _sse_queues:
        _sse_queues[cycle_id] = asyncio.Queue()
    return _sse_queues[cycle_id]


async def _emit(cycle_id: str, event: dict[str, Any]) -> None:
    """Push an event to the SSE queue for this cycle."""
    q = _sse_queues.get(cycle_id)
    if q:
        await q.put(event)


async def _run_agent_cycle(
    cycle_id: str,
    user: dict,
    db,
    image_b64: str | None = None,
) -> None:
    """Background task: run the dynamic multi-agent pipeline, save to MongoDB, emit SSE events."""
    import logging
    from backend.agents.graph import agent_graph
    from backend.memory.memory_manager import save_memory
    from backend.memory.summarizer import generate_cycle_memory
    from backend.observability.tracer import ExecutionTracer

    logger = logging.getLogger(__name__)
    farmer_id = str(user.get("_id", ""))
    tracer = ExecutionTracer(cycle_id, farmer_id)

    await db["agent_cycles"].update_one(
        {"cycle_id": cycle_id},
        {"$set": {"status": "running"}},
    )
    await _emit(cycle_id, {"event": "status", "agent": "pipeline", "status": "running"})

    # Memory is now loaded inside the graph via MemoryTool node
    # (kept here as empty initial values; the graph fills them)
    initial_state: AgentState = {
        "cycle_id": cycle_id,
        "farmer_id": farmer_id,
        "weather_forecast": {},
        "crop_prices": {},
        "farm_state": {
            "primary_crops": user.get("primary_crops", ["tomato", "brinjal", "cabbage", "lemon"]),
            "location": user.get("location", "Guwahati, Assam"),
            "username": user.get("username", ""),
            "farm_size_acres": user.get("farm_size_acres"),
        },
        # Memory (filled by MemoryTool node in graph)
        "memory_context": "",
        "selected_memories": [],
        "memory_retrieval_query": "",
        # Weather
        "weather_interpretation": "",
        "planting_advice": "",
        "irrigation_advice": "",
        "weather_alerts": [],
        "weather_confidence": 0.0,
        # Market
        "market_analysis": "",
        "sell_hold_decisions": {},
        "price_alerts": [],
        "best_selling_window": "",
        "market_confidence": 0.0,
        # Advisory
        "rag_query": "",
        "rag_sources": [],
        "crop_advisory": "",
        "pest_warnings": [],
        "advisory_confidence": 0.0,
        # Supervisor
        "final_report": "",
        "all_alerts": [],
        "top_recommendations": [],
        "supervisor_confidence": 0.0,
        "decision_graph": {},
        # Planner
        "planner_decision": {},
        "intent": "",
        # Judge
        "judge_output": {},
        # Multimodal
        "disease_image_b64": image_b64,
        "disease_detection": {},
        # Schemes
        "scheme_info": [],
        # Timing
        "agent_timings": {},
        # Trace (populated by tracer after completion)
        "trace": {},
        "error": None,
    }

    try:
        result: AgentState = await agent_graph.ainvoke(initial_state)
        completed_at = datetime.utcnow()

        timings = result.get("agent_timings", {})

        # Emit per-node SSE events (includes new nodes: planner, memory, judge)
        for node_name in ["fetching", "memory", "planner", "weather", "market", "advisory", "disease", "judge", "supervisor"]:
            if node_name in timings:
                await _emit(cycle_id, {
                    "event": "agent_done",
                    "agent": node_name,
                    "time_ms": timings[node_name],
                })

        # Emit planner decision
        if result.get("planner_decision"):
            pd = result["planner_decision"]
            await _emit(cycle_id, {
                "event": "planner",
                "intent": pd.get("intent", ""),
                "selected_tools": pd.get("selected_tools", []),
                "reasoning": pd.get("reasoning", ""),
            })

        # Emit judge verdict
        if result.get("judge_output"):
            jo = result["judge_output"]
            await _emit(cycle_id, {
                "event": "judge",
                "verdict": jo.get("verdict", "pass"),
                "issues": jo.get("issues", []),
            })

        # --- Save farmer memory ---
        try:
            memory_text = await generate_cycle_memory(result)
            await save_memory(
                farmer_id=farmer_id,
                cycle_id=cycle_id,
                weather_summary=f"{result.get('weather_forecast', {}).get('Condition', 'N/A')}, "
                                f"{result.get('weather_forecast', {}).get('Temperature', '?')}°C",
                market_summary="; ".join(
                    f"{c}: {d}" for c, d in result.get("sell_hold_decisions", {}).items()
                ),
                recommendation_summary="; ".join(result.get("top_recommendations", [])[:3]),
                disease_alerts=result.get("pest_warnings", [])[:3],
                memory_text=memory_text,
            )
        except Exception as e:
            logger.warning("Memory save failed: %s", e)

        # --- Generate and persist smart notifications ---
        try:
            from backend.utils.notification_generator import generate_notifications, persist_notifications
            from backend.utils.email_sender import send_notification_email
            from backend.routers.notifications import ws_manager

            notifications = generate_notifications(dict(result))
            n_saved = await persist_notifications(db, user["_id"], notifications, cycle_id)

            if n_saved > 0:
                await ws_manager.push(farmer_id, {
                    "event": "notifications_updated",
                    "count": n_saved,
                    "cycle_id": cycle_id,
                })
                await _emit(cycle_id, {"event": "notifications", "count": n_saved})

                user_email = user.get("email", "")
                username   = user.get("username", "Farmer")
                if user_email:
                    await send_notification_email(user_email, username, notifications)
        except Exception as e:
            logger.warning("Notification generation failed: %s", e)

        # --- Save observability trace ---
        try:
            tracer.finalize_from_state(dict(result))
            await tracer.save(db)
        except Exception as e:
            logger.warning("Tracer save failed: %s", e)

        # Build agents_output array (backward compat + new nodes)
        agents_output = []
        for node, label, summary_key, in_key in [
            ("fetching",  "FetchingAgent",  "weather_forecast",       "ML models + Live/SARIMAX data"),
            ("memory",    "MemoryTool",     "memory_context",         "farmer_id + semantic query"),
            ("planner",   "PlannerAgent",   "planner_decision",       "farm_state + intent detection"),
            ("weather",   "WeatherAgent",   "weather_interpretation",  "weather forecast data"),
            ("market",    "MarketAgent",    "market_analysis",         "crop prices + weather context"),
            ("advisory",  "AdvisoryAgent",  "crop_advisory",           result.get("rag_query", "")),
            ("disease",   "DiseaseTool",    "disease_detection",       "leaf image (if provided)"),
            ("judge",     "JudgeAgent",     "judge_output",            "final_report + raw data"),
            ("supervisor","SupervisorAgent","final_report",            "all agent outputs + memory"),
        ]:
            if timings.get(node) is not None or result.get(summary_key):
                out = result.get(summary_key, "")
                agents_output.append({
                    "agent_name":        label,
                    "input_summary":     in_key if isinstance(in_key, str) else str(in_key),
                    "output":            str(out)[:500] if out else "",
                    "execution_time_ms": timings.get(node, 0),
                    "confidence":        result.get(f"{node}_confidence", 0),
                })

        await db["agent_cycles"].update_one(
            {"cycle_id": cycle_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": completed_at,
                    "weather_data": result.get("weather_forecast", {}),
                    "price_data": result.get("crop_prices", {}),
                    "final_report": result.get("final_report", ""),
                    "alerts": result.get("all_alerts", []),
                    "recommendations": result.get("top_recommendations", []),
                    "sell_hold_decisions": result.get("sell_hold_decisions", {}),
                    "best_selling_window": result.get("best_selling_window", ""),
                    "decision_graph": result.get("decision_graph", {}),
                    "agent_timings": timings,
                    "rag_sources": result.get("rag_sources", []),
                    "planner_decision": result.get("planner_decision", {}),
                    "intent": result.get("intent", ""),
                    "judge_output": result.get("judge_output", {}),
                    "disease_detection": result.get("disease_detection", {}),
                    "confidences": {
                        "weather":    result.get("weather_confidence", 0),
                        "market":     result.get("market_confidence", 0),
                        "advisory":   result.get("advisory_confidence", 0),
                        "supervisor": result.get("supervisor_confidence", 0),
                    },
                    "agents_output": agents_output,
                }
            },
        )
        await _emit(cycle_id, {"event": "status", "agent": "pipeline", "status": "completed"})

    except Exception as exc:
        await db["agent_cycles"].update_one(
            {"cycle_id": cycle_id},
            {"$set": {"status": "failed", "final_report": str(exc), "completed_at": datetime.utcnow()}},
        )
        await _emit(cycle_id, {"event": "status", "agent": "pipeline", "status": "failed", "error": str(exc)})
    finally:
        # Send sentinel to close SSE connections
        await _emit(cycle_id, None)
        _sse_queues.pop(cycle_id, None)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/run-cycle")
async def run_cycle(
    background_tasks: BackgroundTasks,
    body: RunCycleRequest = RunCycleRequest(),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    cycle_id = str(uuid.uuid4())
    _get_queue(cycle_id)  # pre-create queue before background task starts

    doc = {
        "cycle_id": cycle_id,
        "triggered_by": "manual",
        "user_id": current_user["_id"],
        "started_at": datetime.utcnow(),
        "status": "queued",
        "weather_data": {},
        "price_data": {},
        "agents_output": [],
        "final_report": "",
        "alerts": [],
        "recommendations": [],
        "sell_hold_decisions": {},
        "has_image": body.image_base64 is not None,
    }
    await db["agent_cycles"].insert_one(doc)
    background_tasks.add_task(_run_agent_cycle, cycle_id, current_user, db, body.image_base64)

    return {"cycle_id": cycle_id, "status": "queued", "message": "Agent cycle started"}


@router.get("/stream/{cycle_id}")
async def stream_cycle(
    cycle_id: str,
    request: Request,
    _user=Depends(get_current_user),
):
    """
    SSE endpoint. Frontend connects here to receive real-time agent progress.
    Events: {event, agent, status/time_ms/...}
    Connection closes automatically when pipeline finishes.
    """
    queue = _get_queue(cycle_id)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=120.0)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'event': 'heartbeat'})}\n\n"
                    continue
                if event is None:  # sentinel — pipeline done
                    yield f"data: {json.dumps({'event': 'done'})}\n\n"
                    break
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@router.get("/latest-report")
async def latest_report(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    cycle = await db["agent_cycles"].find_one(
        {"status": "completed"},
        sort=[("completed_at", -1)],
    )
    if not cycle:
        cycle = await db["agent_cycles"].find_one({}, sort=[("started_at", -1)])
    if not cycle:
        return {"message": "No cycles yet. Click Run AI Analysis to start.", "cycle": None}
    cycle["_id"] = str(cycle["_id"])
    return cycle


@router.get("/status/{cycle_id}")
async def cycle_status(
    cycle_id: str,
    _user=Depends(get_current_user),
    db=Depends(get_db),
):
    cycle = await db["agent_cycles"].find_one({"cycle_id": cycle_id})
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    cycle["_id"] = str(cycle["_id"])
    return {
        "cycle_id": cycle_id,
        "status": cycle["status"],
        "completed_at": cycle.get("completed_at"),
        "agent_timings": cycle.get("agent_timings", {}),
    }


@router.get("/history")
async def cycle_history(_user=Depends(get_current_user), db=Depends(get_db)):
    cycles = await db["agent_cycles"].find(
        {}, {"final_report": 0, "agents_output": 0}
    ).sort("started_at", -1).to_list(20)
    for c in cycles:
        c["_id"] = str(c["_id"])
    return cycles


@router.get("/memory")
async def farmer_memory(current_user: dict = Depends(get_current_user)):
    """Return the last 20 farmer memory entries."""
    from backend.memory.memory_manager import get_recent_memories
    memories = await get_recent_memories(str(current_user["_id"]), limit=20)
    return {"memories": memories, "count": len(memories)}
