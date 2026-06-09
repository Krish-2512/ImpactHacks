import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from bson import ObjectId
from backend.auth.dependencies import get_current_user
from backend.database.mongodb import get_db
from backend.agents.state import AgentState

router = APIRouter()


async def _run_agent_cycle(cycle_id: str, user: dict, db):
    """Background task: run the full 5-agent pipeline and save result to MongoDB."""
    from backend.agents.graph import agent_graph

    # Update status to running
    await db["agent_cycles"].update_one(
        {"cycle_id": cycle_id},
        {"$set": {"status": "running"}},
    )

    initial_state: AgentState = {
        "cycle_id": cycle_id,
        "weather_forecast": {},
        "crop_prices": {},
        "farm_state": {
            "primary_crops": user.get("primary_crops", ["tomato", "brinjal", "cabbage", "lemon"]),
            "location": user.get("location", "Guwahati, Assam"),
            "username": user.get("username", ""),
        },
        "weather_interpretation": "",
        "planting_advice": "",
        "irrigation_advice": "",
        "weather_alerts": [],
        "market_analysis": "",
        "sell_hold_decisions": {},
        "price_alerts": [],
        "best_selling_window": "",
        "rag_query": "",
        "crop_advisory": "",
        "pest_warnings": [],
        "final_report": "",
        "all_alerts": [],
        "top_recommendations": [],
        "error": None,
    }

    try:
        result: AgentState = await agent_graph.ainvoke(initial_state)
        completed_at = datetime.utcnow()

        await db["agent_cycles"].update_one(
            {"cycle_id": cycle_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": completed_at,
                    "weather_data": result["weather_forecast"],
                    "price_data": result["crop_prices"],
                    "final_report": result["final_report"],
                    "alerts": result["all_alerts"],
                    "recommendations": result["top_recommendations"],
                    "sell_hold_decisions": result["sell_hold_decisions"],
                    "agents_output": [
                        {"agent_name": "WeatherAgent",   "input_summary": "weather forecast data",    "output": result.get("weather_interpretation", ""), "execution_time_ms": 0},
                        {"agent_name": "MarketAgent",    "input_summary": "crop price predictions",   "output": result.get("market_analysis", ""),        "execution_time_ms": 0},
                        {"agent_name": "AdvisoryAgent",  "input_summary": result.get("rag_query", ""), "output": result.get("crop_advisory", ""),          "execution_time_ms": 0},
                        {"agent_name": "SupervisorAgent","input_summary": "all agent outputs",         "output": result.get("final_report", ""),           "execution_time_ms": 0},
                    ],
                }
            },
        )
    except Exception as exc:
        await db["agent_cycles"].update_one(
            {"cycle_id": cycle_id},
            {"$set": {"status": "failed", "final_report": str(exc), "completed_at": datetime.utcnow()}},
        )


@router.post("/run-cycle")
async def run_cycle(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    cycle_id = str(uuid.uuid4())
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
    }
    await db["agent_cycles"].insert_one(doc)
    background_tasks.add_task(_run_agent_cycle, cycle_id, current_user, db)

    return {"cycle_id": cycle_id, "status": "queued", "message": "Agent cycle started"}


@router.get("/latest-report")
async def latest_report(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    # Try completed first, then fall back to most recent (including failed) so errors are visible
    cycle = await db["agent_cycles"].find_one(
        {"status": "completed"},
        sort=[("completed_at", -1)],
    )
    if not cycle:
        cycle = await db["agent_cycles"].find_one(
            {}, sort=[("started_at", -1)]
        )
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
    return {"cycle_id": cycle_id, "status": cycle["status"], "completed_at": cycle.get("completed_at")}


@router.get("/history")
async def cycle_history(_user=Depends(get_current_user), db=Depends(get_db)):
    cycles = await db["agent_cycles"].find(
        {}, {"final_report": 0, "agents_output": 0}
    ).sort("started_at", -1).to_list(20)
    for c in cycles:
        c["_id"] = str(c["_id"])
    return cycles
