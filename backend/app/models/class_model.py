from pydantic import BaseModel, Field

from app.models.base import MongoBaseModel, utc_now
from datetime import datetime


class ClassModel(MongoBaseModel):
    map_id: str = Field(..., examples=["10"])
    class_id: str | None = None
    name: str = Field(..., examples=["Lớp 10"])
    grade: int | None = None
    section: str | None = None
    createdAt: datetime = Field(default_factory=utc_now)
    updatedAt: datetime = Field(default_factory=utc_now)
