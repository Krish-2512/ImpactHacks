from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from backend.config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    global _client, _db
    _client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=5000,  # 5s timeout so startup isn't blocked forever
    )
    _db = _client[settings.MONGODB_DB_NAME]
    try:
        await _db["users"].create_index("email", unique=True)
        await _db["users"].create_index("username", unique=True)
        await _db["products"].create_index("farmer_id")
        await _db["sales"].create_index([("seller_id", 1), ("sold_at", -1)])
        await _db["notifications"].create_index([("user_id", 1), ("is_read", 1)])
        await _db["agent_cycles"].create_index([("started_at", -1)])
        print(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")
    except Exception as e:
        print(f"[WARNING] MongoDB not reachable ({e}). Set MONGODB_URI in .env and restart.")


async def close_db() -> None:
    global _client
    if _client:
        _client.close()


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Database not available. Set MONGODB_URI in .env and restart the server.",
        )
    return _db
