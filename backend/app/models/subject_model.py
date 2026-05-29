from datetime import datetime
from pydantic import Field

from app.models.base import MongoBaseModel, utc_now


class SubjectModel(MongoBaseModel):
    map_id: str = Field(..., examples=["TH10"])
    subject_id: str | None = None
    metadata_id: str | None = None
    name: str = Field(..., examples=["Tin học"])
    filePath: str | None = ""
    classMapId: str = Field(..., examples=["10"])
    class_id: str | None = None
    description: str | None = None
    createdAt: datetime = Field(default_factory=utc_now)
    updatedAt: datetime = Field(default_factory=utc_now)
