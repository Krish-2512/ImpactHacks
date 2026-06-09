from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from backend.auth.service import decode_token
from backend.database.mongodb import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    from bson import ObjectId
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise credentials_exception

    user["_id"] = str(user["_id"])
    return user


async def require_farmer(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "farmer":
        raise HTTPException(status_code=403, detail="Farmer account required")
    return current_user
