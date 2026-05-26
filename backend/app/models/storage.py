from datetime import datetime
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    sourceName: str | None = None
    sourceUrl: str | None = None
    originalFileName: str
    mimeType: str
    fileSizeBytes: int | None = None
    language: str = "vi"
    collectedAt: datetime | None = None
    licenseNote: str | None = None


class StorageInfo(BaseModel):
    provider: str = "google_drive"

    # Logical path used by the app. Kept compatible with the old MinIO objectKey.
    objectKey: str

    # Google Drive identifiers and links.
    rootFolderId: str | None = None
    folderId: str | None = None
    fileId: str | None = None
    webViewLink: str | None = None
    webContentLink: str | None = None

    # File metadata returned by Google Drive.
    mimeType: str | None = None
    sizeBytes: int | None = None

    # Legacy fields kept optional so old MongoDB documents can still deserialize.
    bucket: str | None = None
    etag: str | None = None


class DocumentContent(BaseModel):
    summary: str | None = None
    tableOfContents: list[str] = Field(default_factory=list)
    hasImages: bool = False
    hasTables: bool = False
    hasExercises: bool = False
    hasAnswerKey: bool = False


class StemInfo(BaseModel):
    stemProblem: str | None = None
    stemProduct: str | None = None
    science: list[str] = Field(default_factory=list)
    technology: list[str] = Field(default_factory=list)
    engineering: list[str] = Field(default_factory=list)
    math: list[str] = Field(default_factory=list)
