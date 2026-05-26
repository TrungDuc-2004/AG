from typing import Any

from pydantic import BaseModel, Field


class KeywordSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=50)


class PathNode(BaseModel):
    id: str | None = None
    name: str | None = None
    title: str | None = None
    file_path: str | None = None


class MatchedKeyword(BaseModel):
    keyword_id: str | None = None
    keyword_name: str
    aliases: list[str] = []


class KeywordSearchResult(BaseModel):
    score: float
    result_type: str = "document"
    match_type: str = "exact_keyword"

    subject: PathNode | None = None
    topic: PathNode | None = None
    concept: PathNode | None = None
    document: PathNode | None = None

    matched_keywords: list[MatchedKeyword] = []
    document_keywords: list[str] = []

    content_preview: str | None = None
    file_path: str | None = None
    page_start: int | None = None
    page_end: int | None = None

    raw: dict[str, Any] = {}


class LevelSearchResult(BaseModel):
    result_type: str
    score: float
    id: str | None = None
    name: str | None = None
    title: str | None = None
    file_path: str | None = None

    matched_document_count: int = 0
    matched_keywords: list[str] = []

    subject: PathNode | None = None
    topic: PathNode | None = None
    concept: PathNode | None = None
    document: PathNode | None = None


class KeywordSearchGroups(BaseModel):
    subjects: list[LevelSearchResult] = []
    topics: list[LevelSearchResult] = []
    concepts: list[LevelSearchResult] = []
    documents: list[LevelSearchResult] = []


class KeywordSearchResponse(BaseModel):
    query: str
    extracted_keywords: list[str]
    results: list[KeywordSearchResult]
    groups: KeywordSearchGroups
