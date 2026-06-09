from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime
from backend.auth.schemas import UserCreate, UserLogin, UserUpdateRequest, TokenResponse
from backend.auth.service import hash_password, verify_password, create_access_token
from backend.auth.dependencies import get_current_user
from backend.database.mongodb import get_db

router = APIRouter()


@router.post("/register", status_code=201)
async def register(payload: UserCreate, db=Depends(get_db)):
    if await db["users"].find_one({"email": payload.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await db["users"].find_one({"username": payload.username}):
        raise HTTPException(status_code=400, detail="Username already taken")

    user_doc = {
        "username": payload.username,
        "email": payload.email,
        "hashed_password": hash_password(payload.password),
        "role": payload.role,
        "phone": payload.phone,
        "location": payload.location,
        "primary_crops": payload.primary_crops,
        "farm_size_acres": payload.farm_size_acres,
        "created_at": datetime.utcnow(),
        "is_active": True,
    }
    result = await db["users"].insert_one(user_doc)
    user_id = str(result.inserted_id)

    token = create_access_token({"sub": user_id, "role": payload.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "_id": user_id,
            "username": payload.username,
            "email": payload.email,
            "role": payload.role,
            "location": payload.location,
            "primary_crops": payload.primary_crops,
        },
    }


@router.post("/login")
async def login(payload: UserLogin, db=Depends(get_db)):
    user = await db["users"].find_one({"email": payload.email})
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    user_id = str(user["_id"])
    token = create_access_token({"sub": user_id, "role": user.get("role", "farmer")})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "_id": user_id,
            "username": user["username"],
            "email": user["email"],
            "role": user.get("role", "farmer"),
            "location": user.get("location"),
            "primary_crops": user.get("primary_crops", []),
        },
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    current_user.pop("hashed_password", None)
    return current_user


@router.put("/me")
async def update_me(
    payload: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    from bson import ObjectId
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await db["users"].update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$set": update_data},
    )
    return {"message": "Profile updated"}
