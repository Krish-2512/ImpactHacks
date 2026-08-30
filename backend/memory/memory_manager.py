from datetime import datetime, date
from typing import List
from backend.database.mongodb import get_db
import logging

logger = logging.getLogger(__name__)


async def get_recent_memories(farmer_id: str, limit: int = 20) -> List[dict]:
    """Fetch the last `limit` cycle memories for this farmer, newest first."""
    db = get_db()
    docs = await db["farmer_memory"].find(
        {"farmer_id": farmer_id},
        {"_id": 0},
    ).sort("date", -1).limit(limit).to_list(limit)
    return docs


async def save_memory(
    farmer_id: str,
    cycle_id: str,
    weather_summary: str,
    market_summary: str,
    recommendation_summary: str,
    disease_alerts: List[str],
    memory_text: str,
) -> None:
    """Persist one cycle's memory entry to MongoDB."""
    db = get_db()
    doc = {
        "farmer_id": farmer_id,
        "cycle_id": cycle_id,
        "date": date.today().isoformat(),
        "weather_summary": weather_summary,
        "market_summary": market_summary,
        "recommendation_summary": recommendation_summary,
        "disease_alerts": disease_alerts,
        "memory_text": memory_text,
        "created_at": datetime.utcnow(),
    }
    # Upsert by cycle_id so re-runs don't create duplicates
    await db["farmer_memory"].update_one(
        {"cycle_id": cycle_id},
        {"$set": doc},
        upsert=True,
    )

    # Also store embedding in Qdrant for semantic retrieval
    try:
        from backend.memory.memory_vectorstore import save_memory_embedding
        await save_memory_embedding(
            farmer_id=farmer_id,
            cycle_id=cycle_id,
            memory_text=memory_text,
            weather_summary=weather_summary,
            market_summary=market_summary,
            recommendation_summary=recommendation_summary,
            disease_alerts=disease_alerts,
            date=doc["date"],
        )
    except Exception as e:
        logger.warning("Semantic memory save skipped: %s", e)


async def get_memory_count(farmer_id: str) -> int:
    db = get_db()
    return await db["farmer_memory"].count_documents({"farmer_id": farmer_id})
