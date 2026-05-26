from datetime import datetime
from typing import Any
from pydantic import BaseModel

from app.models.enums import EntityType
from app.models.storage import DocumentMetadata, StorageInfo


class EntityFileUploadResponse(BaseModel):
    entityType: EntityType
    map_id: str
    className: str
    entityName: str
    filePath: str
    storage: StorageInfo
    updatedAt: datetime | None = None
    sync: dict[str, Any] | None = None


class DocumentUploadResponse(BaseModel):
    id: str | None = None
    map_id: str
    title: str
    conceptMapId: str
    typedocs: str
    metadata: DocumentMetadata
    storage: StorageInfo
    status: str
    createdBy: str
    updatedBy: str
    createdAt: datetime
    updatedAt: datetime
    sync: dict[str, Any] | None = None


class PresignedUrlResponse(BaseModel):
    # Compatibility response for the old MinIO presigned-url endpoint.
    # With Google Drive, url is a Drive view URL, not a time-limited MinIO URL.
    objectKey: str | None = None
    provider: str = "google_drive"
    fileId: str | None = None
    url: str
    downloadUrl: str | None = None
    expiresSeconds: int
