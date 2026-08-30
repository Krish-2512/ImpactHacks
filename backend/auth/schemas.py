from typing import Optional, List
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "farmer"          # "farmer" | "buyer"
    phone: Optional[str] = None
    location: Optional[str] = None
    primary_crops: List[str] = []
    farm_size_acres: Optional[float] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserUpdateRequest(BaseModel):
    phone: Optional[str] = None
    location: Optional[str] = None
    primary_crops: Optional[List[str]] = None
    farm_size_acres: Optional[float] = None
