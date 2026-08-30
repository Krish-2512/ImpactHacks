from typing import Optional
from datetime import datetime
from pydantic import Field
from backend.models.base import MongoBase, PyObjectId


class SaleDocument(MongoBase):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    product_id: str
    product_name: str
    seller_id: str
    buyer_id: Optional[str] = None
    buyer_name: Optional[str] = None
    quantity_sold: float
    price_per_unit: float
    total_amount: float
    unit: str = "kg"
    sold_at: datetime = Field(default_factory=datetime.utcnow)


class SaleOut(MongoBase):
    id: Optional[str] = Field(default=None, alias="_id")
    product_id: str
    product_name: str
    seller_id: str
    buyer_id: Optional[str]
    buyer_name: Optional[str]
    quantity_sold: float
    price_per_unit: float
    total_amount: float
    unit: str
    sold_at: datetime
