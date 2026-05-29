from datetime import datetime
from pydantic import Field

from app.models.base import MongoBaseModel, utc_now


class TopicModel(MongoBaseModel):
    map_id: str = Field(..., examples=["TH10_T1"])
    topic_id: str | None = None
    metadata_id: str | None = None
    subjectMapId: str = Field(..., examples=["TH10"])
    subject_id: str | None = None
    name: str = Field(..., examples=["Máy tính và cộng đồng"])
    description: str | None = None
    topicNumber: int | None = None
    periodCount: int | None = None
    filePath: str | None = ""
    createdAt: datetime = Field(default_factory=utc_now)
    updatedAt: datetime = Field(default_factory=utc_now)
