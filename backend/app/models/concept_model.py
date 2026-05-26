from datetime import datetime
from pydantic import Field

from app.models.base import MongoBaseModel, utc_now


class ConceptModel(MongoBaseModel):
    map_id: str = Field(..., examples=["TH10_T1_C1"])
    concept_id: str | None = None
    topicMapId: str = Field(..., examples=["TH10_T1"])
    topic_id: str | None = None
    name: str = Field(..., examples=["Thông tin và dữ liệu"])
    filePath: str | None = ""
    definition: str | None = None
    conceptNumber: int | None = None
    createdAt: datetime = Field(default_factory=utc_now)
    updatedAt: datetime = Field(default_factory=utc_now)
