from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from backend.auth.dependencies import get_current_user, require_farmer
from backend.database.mongodb import get_db

router = APIRouter()


class ProductCreate(BaseModel):
    name: str
    price_per_unit: float
    unit: str = "kg"
    quantity_available: float
    description: Optional[str] = None
    location: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price_per_unit: Optional[float] = None
    unit: Optional[str] = None
    quantity_available: Optional[float] = None
    description: Optional[str] = None
    is_available: Optional[bool] = None


class PurchaseRequest(BaseModel):
    quantity: float


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("/products")
async def list_all_products(db=Depends(get_db)):
    products = await db["products"].find({"is_available": True}).to_list(200)
    return [_serialize(p) for p in products]


@router.get("/farmers")
async def list_farmers(db=Depends(get_db)):
    farmers = await db["users"].find(
        {"role": "farmer", "is_active": True},
        {"hashed_password": 0},
    ).to_list(100)
    return [_serialize(f) for f in farmers]


@router.get("/farmer/{farmer_id}/products")
async def farmer_products(farmer_id: str, db=Depends(get_db)):
    products = await db["products"].find(
        {"farmer_id": farmer_id, "is_available": True}
    ).to_list(100)
    return [_serialize(p) for p in products]


@router.post("/products", status_code=201)
async def create_product(
    payload: ProductCreate,
    current_user: dict = Depends(require_farmer),
    db=Depends(get_db),
):
    doc = {
        **payload.model_dump(),
        "farmer_id": current_user["_id"],
        "farmer_name": current_user["username"],
        "location": payload.location or current_user.get("location", ""),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_available": True,
    }
    result = await db["products"].insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    current_user: dict = Depends(require_farmer),
    db=Depends(get_db),
):
    product = await db["products"].find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product["farmer_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not your product")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    await db["products"].update_one({"_id": ObjectId(product_id)}, {"$set": update_data})
    return {"message": "Updated"}


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    current_user: dict = Depends(require_farmer),
    db=Depends(get_db),
):
    product = await db["products"].find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product["farmer_id"] != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not your product")

    await db["products"].update_one(
        {"_id": ObjectId(product_id)}, {"$set": {"is_available": False}}
    )
    return {"message": "Deleted"}


@router.post("/products/{product_id}/purchase")
async def purchase_product(
    product_id: str,
    payload: PurchaseRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    product = await db["products"].find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not product.get("is_available"):
        raise HTTPException(status_code=400, detail="Product not available")
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    if payload.quantity > product["quantity_available"]:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    total = round(product["price_per_unit"] * payload.quantity, 2)

    # Deduct stock
    new_qty = product["quantity_available"] - payload.quantity
    await db["products"].update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"quantity_available": new_qty, "updated_at": datetime.utcnow()}},
    )

    # Record sale
    sale_doc = {
        "product_id": product_id,
        "product_name": product["name"],
        "seller_id": product["farmer_id"],
        "buyer_id": current_user["_id"],
        "buyer_name": current_user["username"],
        "quantity_sold": payload.quantity,
        "price_per_unit": product["price_per_unit"],
        "total_amount": total,
        "unit": product.get("unit", "kg"),
        "sold_at": datetime.utcnow(),
    }
    await db["sales"].insert_one(sale_doc)

    return {
        "success": True,
        "total_amount": total,
        "remaining_stock": new_qty,
        "product_name": product["name"],
    }


@router.get("/transactions")
async def transaction_history(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    user_id = current_user["_id"]
    # Sales where user is seller or buyer
    sales = await db["sales"].find(
        {"$or": [{"seller_id": user_id}, {"buyer_id": user_id}]}
    ).sort("sold_at", -1).to_list(100)
    return [_serialize(s) for s in sales]
