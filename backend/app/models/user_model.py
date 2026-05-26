from datetime import date, datetime
from pydantic import EmailStr, Field

from app.models.base import MongoBaseModel, utc_now


class UserModel(MongoBaseModel):
    map_id: str = Field(..., examples=["USER_001"])
    name: str
    email: EmailStr
    gender: str | None = None
    address: str | None = None
    birthDate: date | None = None
    role: str = Field(..., examples=["1"])
    avatarImage: str | None = None
    createdAt: datetime = Field(default_factory=utc_now)
    updatedAt: datetime = Field(default_factory=utc_now)
