from typing import Optional
from datetime import datetime
from pydantic import Field
from backend.models.base import MongoBase, PyObjectId


class NotificationDocument(MongoBase):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str
    message: str
    message_hi: Optional[str] = None          # Hindi translation
    notification_type: str = "system"         # "weather" | "price_alert" | "agent_report" | "system" | "disease"
    severity: str = "info"                    # "info" | "warning" | "urgent"
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class NotificationOut(MongoBase):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    message: str
    message_hi: Optional[str]
    notification_type: str
    severity: str
    is_read: bool
    created_at: datetime
