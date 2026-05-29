from datetime import datetime
from pydantic import Field

from app.models.base import MongoBaseModel, utc_now
from app.models.storage import DocumentContent, DocumentMetadata, StemInfo, StorageInfo


class DocumentModel(MongoBaseModel):
    map_id: str = Field(..., examples=["TH10_T1_C1_D1"])
    document_id: str | None = None
    title: str
    description: str | None = None
    keysearch: str | None = None
    conceptMapId: str = Field(..., examples=["TH10_T1_C1"])
    concept_id: str | None = None
    typedocs: str = Field(..., examples=["1"])
    metadata: DocumentMetadata
    storage: StorageInfo
    content: DocumentContent | None = None
    stemInfo: StemInfo | None = None
    metadata_id: str | None = None
    filePath: str | None = None
    content_preview: str | None = None
    order_index: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    status: str = "active"
    createdBy: str
    updatedBy: str
    createdAt: datetime = Field(default_factory=utc_now)
    updatedAt: datetime = Field(default_factory=utc_now)
