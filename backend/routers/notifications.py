from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime
from backend.auth.dependencies import get_current_user
from backend.database.mongodb import get_db

router = APIRouter()


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("/")
async def list_notifications(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    notifications = await db["notifications"].find(
        {"user_id": current_user["_id"]}
    ).sort("created_at", -1).to_list(50)
    return [_serialize(n) for n in notifications]


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


async def create_notification(
    db,
    user_id: str,
    message: str,
    notification_type: str = "system",
    severity: str = "info",
    message_hi: str | None = None,
):
    """Helper used by agent pipeline to push notifications to users."""
    await db["notifications"].insert_one({
        "user_id": user_id,
        "message": message,
        "message_hi": message_hi,
        "notification_type": notification_type,
        "severity": severity,
        "is_read": False,
        "created_at": datetime.utcnow(),
    })
