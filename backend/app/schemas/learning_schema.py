from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, EmailStr, Field

from app.models.storage import DocumentContent, DocumentMetadata, StemInfo, StorageInfo


class ClassCreate(BaseModel):
    map_id: str
    name: str


class ClassResponse(ClassCreate):
    id: str | None = None
    createdAt: datetime
    updatedAt: datetime
    sync: dict[str, Any] | None = None


class SubjectCreate(BaseModel):
    map_id: str
    name: str
    filePath: str | None = ""
    classMapId: str
    description: str | None = None


class SubjectResponse(SubjectCreate):
    id: str | None = None
    createdAt: datetime
    updatedAt: datetime
    sync: dict[str, Any] | None = None


class TopicCreate(BaseModel):
    map_id: str
    subjectMapId: str
    name: str
    description: str | None = None
    topicNumber: int | None = None
    periodCount: int | None = None
    filePath: str | None = ""


class TopicResponse(TopicCreate):
    id: str | None = None
    createdAt: datetime
    updatedAt: datetime
    sync: dict[str, Any] | None = None


class ConceptCreate(BaseModel):
    map_id: str
    topicMapId: str
    name: str
    filePath: str | None = ""
    definition: str | None = None
    conceptNumber: int | None = None


class ConceptResponse(ConceptCreate):
    id: str | None = None
    createdAt: datetime
    updatedAt: datetime
    sync: dict[str, Any] | None = None


class DocumentCreate(BaseModel):
    map_id: str
    title: str
    description: str | None = None
    keysearch: str | None = None
    conceptMapId: str
    typedocs: str
    metadata: DocumentMetadata
    storage: StorageInfo
    content: DocumentContent | None = None
    stemInfo: StemInfo | None = None
    status: str = "active"
    createdBy: str
    updatedBy: str


class DocumentResponse(DocumentCreate):
    id: str | None = None
    createdAt: datetime
    updatedAt: datetime
    sync: dict[str, Any] | None = None


class UserCreate(BaseModel):
    map_id: str
    name: str
    email: EmailStr
    gender: str | None = None
    address: str | None = None
    birthDate: date | None = None
    role: str
    avatarImage: str | None = None


class UserResponse(UserCreate):
    id: str | None = None
    createdAt: datetime
    updatedAt: datetime
    sync: dict[str, Any] | None = None
