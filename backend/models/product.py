from typing import Optional
from datetime import datetime
from pydantic import Field
from backend.models.base import MongoBase, PyObjectId


class ProductDocument(MongoBase):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    farmer_id: str
    farmer_name: str
    name: str
    price_per_unit: float
    unit: str = "kg"              # "kg" | "quintal" | "dozen" | "piece"
    quantity_available: float
    location: str = ""
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_available: bool = True


class ProductOut(MongoBase):
    id: Optional[str] = Field(default=None, alias="_id")
    farmer_id: str
    farmer_name: str
    name: str
    price_per_unit: float
    unit: str
    quantity_available: float
    location: str
    description: Optional[str]
    created_at: datetime
    is_available: bool
