from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.auth.schemas import UserCreate, UserLogin, UserUpdateRequest, TokenResponse
from backend.auth.service import hash_password, verify_password, create_access_token
from backend.auth.dependencies import get_current_user
from backend.database.sql import get_sql_db
from backend.database.sql_models import User

router = APIRouter()


@router.post("/register", status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_sql_db)):
    # Check duplicates
    existing_email = await db.execute(select(User).where(User.email == payload.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_username = await db.execute(select(User).where(User.username == payload.username))
    if existing_username.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        phone=payload.phone,
        location=payload.location,
        primary_crops=payload.primary_crops,
        farm_size_acres=payload.farm_size_acres,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.id, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "location": user.location,
            "primary_crops": user.primary_crops or [],
        },
    }


@router.post("/login")
async def login(payload: UserLogin, db: AsyncSession = Depends(get_sql_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token({"sub": user.id, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "location": user.location,
            "primary_crops": user.primary_crops or [],
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
    db: AsyncSession = Depends(get_sql_db),
):
    result = await db.execute(select(User).where(User.id == current_user["_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    return {"message": "Profile updated"}
