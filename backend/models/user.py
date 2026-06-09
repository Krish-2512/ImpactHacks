from typing import Optional, List
from datetime import datetime
from pydantic import Field, EmailStr
from backend.models.base import MongoBase, PyObjectId


class UserDocument(MongoBase):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    username: str
    email: str
    hashed_password: str
    role: str = "farmer"          # "farmer" | "buyer"
    phone: Optional[str] = None
    location: Optional[str] = None
    farm_size_acres: Optional[float] = None
    primary_crops: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class UserOut(MongoBase):
    id: Optional[str] = Field(default=None, alias="_id")
    username: str
    email: str
    role: str
    phone: Optional[str] = None
    location: Optional[str] = None
    primary_crops: List[str] = []
    farm_size_acres: Optional[float] = None
