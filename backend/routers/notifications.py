"""
Notifications router — full-scale implementation.

Features:
- Auto-generated from agent pipeline via rule engine
- Priority-sorted, expiry-aware
- Unread count badge
- Bulk mark-all-read
- WebSocket for real-time push
- DELETE all read
"""
import asyncio
import json
from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from backend.auth.dependencies import get_current_user
from backend.database.mongodb import get_db

router = APIRouter()

# ─── WebSocket connection manager ─────────────────────────────────────────────

class _ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}  # user_id → [ws, ...]

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: str, ws: WebSocket):
        conns = self._connections.get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(user_id, None)

    async def push(self, user_id: str, payload: dict):
        """Push a notification to all active WebSocket connections for this user."""
        conns = self._connections.get(str(user_id), [])
        dead = []
        for ws in conns:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(str(user_id), ws)

    async def broadcast(self, user_ids: list[str], payload: dict):
        await asyncio.gather(*(self.push(uid, payload) for uid in user_ids))


ws_manager = _ConnectionManager()


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("user_id"), ObjectId):
        doc["user_id"] = str(doc["user_id"])
    return doc


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.websocket("/ws")
async def notification_ws(
    ws: WebSocket,
    token: str = Query(...),  # pass JWT as ?token=...
):
    """
    WebSocket for real-time notification push.
    Frontend connects once on login; server pushes whenever new notifications arrive.
    """
    from backend.auth.service import decode_token
    payload = decode_token(token)
    if not payload:
        await ws.close(code=4001)
        return
    user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
    if not user_id:
        await ws.close(code=4001)
        return

    await ws_manager.connect(str(user_id), ws)
    try:
        while True:
            await ws.receive_text()  # keep alive; frontend can send ping
    except WebSocketDisconnect:
        ws_manager.disconnect(str(user_id), ws)


@router.get("/")
async def list_notifications(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
    unread_only: bool = False,
    limit: int = 50,
):
    """
    List notifications for current user.
    Expired notifications are auto-filtered.
    Priority sorted: urgent → high → medium → low.
    """
    query: dict[str, Any] = {
        "user_id": current_user["_id"],
        "$or": [
            {"expires_at": {"$gt": datetime.utcnow()}},
            {"expires_at": {"$exists": False}},
        ],
    }
    if unread_only:
        query["is_read"] = False

    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    docs = await db["notifications"].find(query).sort("created_at", -1).limit(limit).to_list(limit)
    result = [_serialize(d) for d in docs]
    result.sort(key=lambda d: (priority_order.get(d.get("priority", "low"), 4), d.get("created_at", "")))
    return result


@router.get("/count")
async def unread_count(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Fast badge count — returns {unread: N}."""
    count = await db["notifications"].count_documents({
        "user_id": current_user["_id"],
        "is_read": False,
        "$or": [
            {"expires_at": {"$gt": datetime.utcnow()}},
            {"expires_at": {"$exists": False}},
        ],
    })
    return {"unread": count}


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db["notifications"].update_one(
        {"_id": ObjectId(notification_id), "user_id": current_user["_id"]},
        {"$set": {"is_read": True}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}


@router.put("/read-all")
async def mark_all_read(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Mark ALL unread notifications as read in one operation."""
    result = await db["notifications"].update_many(
        {"user_id": current_user["_id"], "is_read": False},
        {"$set": {"is_read": True}},
    )
    return {"marked_read": result.modified_count}


@router.delete("/read")
async def delete_all_read(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete all read notifications (cleanup)."""
    result = await db["notifications"].delete_many(
        {"user_id": current_user["_id"], "is_read": True}
    )
    return {"deleted": result.deleted_count}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    result = await db["notifications"].delete_one(
        {"_id": ObjectId(notification_id), "user_id": current_user["_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Deleted"}


# ─── Internal helper (called by agent pipeline) ───────────────────────────────

async def create_notification(
    db,
    user_id: Any,
    title: str,
    body: str,
    notification_type: str = "system",
    priority: str = "medium",
    confidence: float = 0.0,
    icon: str = "📌",
    cycle_id: str | None = None,
):
    """
    Single notification insert — used for one-off system notifications.
    For bulk pipeline notifications, use notification_generator.persist_notifications().
    """
    from datetime import timedelta
    doc = {
        "user_id": user_id,
        "type": notification_type,
        "priority": priority,
        "title": title,
        "body": body,
        "icon": icon,
        "confidence": confidence,
        "cycle_id": cycle_id,
        "is_read": False,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=48),
    }
    result = await db["notifications"].insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    # Push via WebSocket to connected clients
    await ws_manager.push(str(user_id), {
        "event": "new_notification",
        "notification": _serialize(doc),
    })
    return doc
