import uuid
from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.database.sql import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="farmer")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    farm_size_acres: Mapped[float | None] = mapped_column(Float, nullable=True)
    primary_crops: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_dict(self) -> dict:
        return {
            "_id": self.id,
            "username": self.username,
            "email": self.email,
            "hashed_password": self.hashed_password,
            "role": self.role,
            "phone": self.phone,
            "location": self.location,
            "farm_size_acres": self.farm_size_acres,
            "primary_crops": self.primary_crops or [],
            "created_at": self.created_at,
            "is_active": self.is_active,
        }
