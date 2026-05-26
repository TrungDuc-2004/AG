from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.mongo import ensure_database_ready
from app.models.enums import EntityType
from app.models.storage import DocumentContent, DocumentMetadata, StemInfo, StorageInfo
from app.repositories.learning_repository import (
    ClassRepository,
    ConceptRepository,
    DocumentRepository,
    SubjectRepository,
    TopicRepository,
)
from app.services.extraction.job_service import get_job
from app.services.storage.workspace_service import (
    get_chunk_lesson_dir,
    get_chunk_lesson_keyword_dir,
    get_chunk_pdf_path,
    get_keywords_approved_json_path,
    get_lesson_doc_path,
    get_lessons_approved_json_path,
    get_topic_dir,
    get_topics_approved_json_path,
    read_json,
)
from app.services.storage_service import StorageService
from app.services.sync_service import safe_auto_sync
from app.utils.object_key import build_stem_object_key
from app.utils.slug import safe_filename


PDF_MIME = "application/pdf"


class ExtractPersistenceError(RuntimeError):
    pass


def _number_from_name(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(\d+)", value)
    return int(match.group(1)) if match else None


def _clean_title(*parts: str | None, sep: str = " ") -> str:
    items = [str(part).strip() for part in parts if part and str(part).strip()]
    return sep.join(items).strip()


def _doc_id(lesson_name: str, chunk_name: str) -> str:
    return f"{lesson_name}_{chunk_name}"[:100]


def _metadata_id(document_id: str) -> str:
    return f"META_{document_id}"[:255]


def _keyword_names_from_result(result: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in result.get("keywords") or []:
        if isinstance(item, dict):
            name = str(item.get("keyword_name") or "").strip()
        else:
            name = str(getattr(item, "keyword_name", "") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def _keysearch_from_result(result: dict[str, Any] | None) -> str | None:
    if not result:
        return None
    names = _keyword_names_from_result(result)
    return ", ".join(names) if names else None


class ExtractPersistenceService:
    """Persist reviewed AI-Extract outputs into the STEM data warehouse.

    This service does not change the extraction/cutline logic. It only runs after
    approve/finalize APIs have produced reviewed JSON/PDF artifacts in workspace.
    """

    def __init__(self) -> None:
        self.classes = ClassRepository()
        self.subjects = SubjectRepository()
        self.topics = TopicRepository()
        self.concepts = ConceptRepository()
        self.documents = DocumentRepository()
        self.storage = StorageService()

    async def _ensure_class_subject(
        self,
        *,
        subject_map_id: str | None,
        class_map_id: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        await ensure_database_ready()

        subject_id = subject_map_id or settings.AI_EXTRACT_DEFAULT_SUBJECT_MAP_ID
        class_id = class_map_id or settings.AI_EXTRACT_DEFAULT_CLASS_MAP_ID
        if not subject_id:
            raise ExtractPersistenceError(
                "Missing subjectMapId. Pass ?subjectMapId=... to topic approve "
                "or set AI_EXTRACT_DEFAULT_SUBJECT_MAP_ID in .env/config.env."
            )

        subject_doc = await self.subjects.find_by_map_id(subject_id)
        if subject_doc:
            class_ref = subject_doc.get("classMapId") or subject_doc.get("class_id")
            class_doc = await self.classes.find_by_map_id(str(class_ref)) if class_ref else None
            if not class_doc:
                raise ExtractPersistenceError(f"Class of subject {subject_id!r} was not found.")
            return class_doc, subject_doc

        if not class_id:
            raise ExtractPersistenceError(
                f"Subject {subject_id!r} does not exist. Pass ?classMapId=... so it can be created, "
                "or create the subject before approving topics."
            )

        class_doc = await self.classes.find_by_map_id(class_id)
        if not class_doc:
            class_doc = await self.classes.upsert_by_map_id(
                class_id,
                {
                    "map_id": class_id,
                    "class_id": class_id,
                    "name": class_id,
                    "grade": _number_from_name(class_id),
                    "section": class_id,
                },
            )
            await safe_auto_sync("classes", class_id)

        subject_doc = await self.subjects.upsert_by_map_id(
            subject_id,
            {
                "map_id": subject_id,
                "subject_id": subject_id,
                "name": subject_id,
                "classMapId": class_id,
                "class_id": class_id,
                "description": None,
                "filePath": "",
            },
        )
        await safe_auto_sync("subjects", subject_id)
        return class_doc, subject_doc

    async def _upload_pdf(
        self,
        *,
        class_name: str,
        entity_type: EntityType,
        entity_name: str,
        pdf_path: Path,
    ) -> dict[str, Any]:
        object_key = build_stem_object_key(
            class_name=class_name,
            entity_type=entity_type,
            entity_name=entity_name,
            original_filename=safe_filename(pdf_path.name),
        )
        return await self.storage.upload_local_file(
            path=pdf_path,
            object_key=object_key,
            content_type=PDF_MIME,
        )

    async def persist_topics(
        self,
        *,
        job_id: str,
        subject_map_id: str | None = None,
        class_map_id: str | None = None,
    ) -> dict[str, Any]:
        get_job(job_id)
        topics_path = get_topics_approved_json_path(job_id)
        if not topics_path.exists():
            raise FileNotFoundError("Approved topics JSON was not found.")
        topics = read_json(topics_path)
        if not isinstance(topics, list):
            raise ValueError(f"Expected topics list in {topics_path}")

        class_doc, subject_doc = await self._ensure_class_subject(
            subject_map_id=subject_map_id,
            class_map_id=class_map_id,
        )
        class_name = str(class_doc.get("name") or class_doc.get("section") or class_doc.get("map_id") or "class")
        subject_id = str(subject_doc.get("map_id") or subject_doc.get("subject_id"))

        persisted: list[dict[str, Any]] = []
        for topic in topics:
            if not isinstance(topic, dict):
                continue
            topic_id = str(topic.get("name") or "").strip()
            if not topic_id:
                continue
            title = str(topic.get("title") or topic_id).strip()
            topic_pdf = get_topic_dir(job_id) / "doc" / f"{topic_id}.pdf"
            file_path = ""
            storage_info = None
            if topic_pdf.exists():
                storage_info = await self._upload_pdf(
                    class_name=class_name,
                    entity_type=EntityType.topics,
                    entity_name=title,
                    pdf_path=topic_pdf,
                )
                file_path = storage_info["objectKey"]

            doc = await self.topics.upsert_by_map_id(
                topic_id,
                {
                    "map_id": topic_id,
                    "topic_id": topic_id,
                    "subjectMapId": subject_id,
                    "subject_id": subject_id,
                    "name": title,
                    "description": topic.get("heading"),
                    "topicNumber": _number_from_name(topic_id),
                    "filePath": file_path,
                },
            )
            sync = await safe_auto_sync("topics", topic_id)
            persisted.append({"topic_id": topic_id, "mongo_id": doc.get("id"), "filePath": file_path, "storage": storage_info, "sync": sync})

        return {"entity": "topics", "count": len(persisted), "items": persisted}

    async def persist_lessons(self, *, job_id: str) -> dict[str, Any]:
        get_job(job_id)
        lessons_path = get_lessons_approved_json_path(job_id)
        if not lessons_path.exists():
            raise FileNotFoundError("Approved lessons JSON was not found.")
        lessons = read_json(lessons_path)
        if not isinstance(lessons, list):
            raise ValueError(f"Expected lessons list in {lessons_path}")

        persisted: list[dict[str, Any]] = []
        for lesson in lessons:
            if not isinstance(lesson, dict):
                continue
            lesson_id = str(lesson.get("name") or "").strip()
            topic_id = str(lesson.get("topic_name") or "").strip()
            if not lesson_id or not topic_id:
                continue

            topic_doc = await self.topics.find_by_map_id(topic_id)
            if not topic_doc:
                raise ExtractPersistenceError(f"Topic {topic_id!r} must be persisted before lesson {lesson_id!r}.")
            subject_doc = await self.subjects.find_by_map_id(str(topic_doc.get("subjectMapId") or topic_doc.get("subject_id")))
            if not subject_doc:
                raise ExtractPersistenceError(f"Subject of topic {topic_id!r} was not found.")
            class_doc = await self.classes.find_by_map_id(str(subject_doc.get("classMapId") or subject_doc.get("class_id")))
            if not class_doc:
                raise ExtractPersistenceError(f"Class of topic {topic_id!r} was not found.")

            class_name = str(class_doc.get("name") or class_doc.get("section") or class_doc.get("map_id") or "class")
            lesson_title = _clean_title(lesson.get("heading"), lesson.get("title"), sep=" - ") or lesson_id
            lesson_pdf = get_lesson_doc_path(job_id, lesson_id)
            file_path = ""
            storage_info = None
            if lesson_pdf.exists():
                storage_info = await self._upload_pdf(
                    class_name=class_name,
                    entity_type=EntityType.concepts,
                    entity_name=lesson_title,
                    pdf_path=lesson_pdf,
                )
                file_path = storage_info["objectKey"]

            doc = await self.concepts.upsert_by_map_id(
                lesson_id,
                {
                    "map_id": lesson_id,
                    "concept_id": lesson_id,
                    "topicMapId": topic_id,
                    "topic_id": topic_id,
                    "name": lesson_title,
                    "definition": None,
                    "conceptNumber": _number_from_name(lesson_id),
                    "filePath": file_path,
                },
            )
            sync = await safe_auto_sync("concepts", lesson_id)
            persisted.append({"concept_id": lesson_id, "mongo_id": doc.get("id"), "filePath": file_path, "storage": storage_info, "sync": sync})

        return {"entity": "concepts", "count": len(persisted), "items": persisted}

    def _load_lesson(self, *, job_id: str, lesson_name: str) -> dict[str, Any]:
        lessons_path = get_lessons_approved_json_path(job_id)
        if not lessons_path.exists():
            raise FileNotFoundError("Approved lessons JSON was not found.")
        lessons = read_json(lessons_path)
        for lesson in lessons if isinstance(lessons, list) else []:
            if isinstance(lesson, dict) and lesson.get("name") == lesson_name:
                return lesson
        raise FileNotFoundError(f"Lesson {lesson_name!r} was not found in approved lessons.")

    def _load_chunks(self, *, job_id: str, lesson_name: str) -> list[dict[str, Any]]:
        approved_path = get_chunk_lesson_dir(job_id, lesson_name) / "chunks_approved.json"
        if approved_path.exists():
            payload = read_json(approved_path)
            chunks = payload.get("chunks") if isinstance(payload, dict) else None
            if isinstance(chunks, list):
                return [chunk for chunk in chunks if isinstance(chunk, dict)]

        lesson_dir = get_chunk_lesson_dir(job_id, lesson_name)
        chunks: list[dict[str, Any]] = []
        for path in sorted(lesson_dir.glob("chunk_*.json")):
            payload = read_json(path)
            if isinstance(payload, dict):
                chunks.append(payload)
        return chunks

    def _load_keyword_results(self, *, job_id: str, lesson_name: str) -> dict[str, dict[str, Any]]:
        approved_path = get_keywords_approved_json_path(job_id, lesson_name)
        results: list[dict[str, Any]] = []
        if approved_path.exists():
            payload = read_json(approved_path)
            if isinstance(payload, dict) and isinstance(payload.get("results"), list):
                results = [item for item in payload["results"] if isinstance(item, dict)]
        else:
            keyword_dir = get_chunk_lesson_keyword_dir(job_id, lesson_name)
            if keyword_dir.exists():
                for path in sorted(keyword_dir.glob("keyword_chunk_*.json")):
                    payload = read_json(path)
                    if isinstance(payload, dict):
                        results.append(payload)
        return {str(item.get("chunk_name")): item for item in results if item.get("chunk_name")}

    async def persist_lesson_documents(
        self,
        *,
        job_id: str,
        lesson_name: str,
        upload_documents: bool = True,
    ) -> dict[str, Any]:
        get_job(job_id)
        lesson = self._load_lesson(job_id=job_id, lesson_name=lesson_name)
        concept_id = str(lesson.get("name") or lesson_name)
        topic_id = str(lesson.get("topic_name") or "").strip()
        if not topic_id:
            raise ExtractPersistenceError(f"Lesson {lesson_name!r} has no topic_name.")

        concept_doc = await self.concepts.find_by_map_id(concept_id)
        if not concept_doc:
            # This keeps the finalization route usable if the caller forgot to approve-lessons persistence.
            await self.persist_lessons(job_id=job_id)
            concept_doc = await self.concepts.find_by_map_id(concept_id)
        if not concept_doc:
            raise ExtractPersistenceError(f"Concept {concept_id!r} was not found.")

        topic_doc = await self.topics.find_by_map_id(topic_id)
        if not topic_doc:
            raise ExtractPersistenceError(f"Topic {topic_id!r} must be persisted before documents.")
        subject_doc = await self.subjects.find_by_map_id(str(topic_doc.get("subjectMapId") or topic_doc.get("subject_id")))
        class_doc = await self.classes.find_by_map_id(str(subject_doc.get("classMapId") or subject_doc.get("class_id"))) if subject_doc else None
        if not class_doc:
            raise ExtractPersistenceError(f"Class context for topic {topic_id!r} was not found.")
        class_name = str(class_doc.get("name") or class_doc.get("section") or class_doc.get("map_id") or "class")

        chunks = self._load_chunks(job_id=job_id, lesson_name=lesson_name)
        keyword_by_chunk = self._load_keyword_results(job_id=job_id, lesson_name=lesson_name)
        persisted: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        for chunk in chunks:
            chunk_name = str(chunk.get("name") or "").strip()
            if not chunk_name:
                continue
            document_id = _doc_id(lesson_name, chunk_name)
            title = _clean_title(chunk.get("heading"), chunk.get("title")) or document_id
            chunk_pdf = get_chunk_pdf_path(job_id, lesson_name, chunk_name)
            if upload_documents and not chunk_pdf.exists():
                raise FileNotFoundError(f"Chunk PDF was not found: {chunk_pdf}")

            existing = await self.documents.find_by_map_id(document_id)
            storage_info = existing.get("storage") if existing else None
            if upload_documents:
                storage_info = await self._upload_pdf(
                    class_name=class_name,
                    entity_type=EntityType.documents,
                    entity_name=title,
                    pdf_path=chunk_pdf,
                )
            if not storage_info:
                raise ExtractPersistenceError(f"Document {document_id!r} has no storage info. Run finalize persistence first.")

            keyword_result = keyword_by_chunk.get(chunk_name)
            keysearch = _keysearch_from_result(keyword_result)
            page_start = chunk.get("start")
            page_end = chunk.get("end")
            try:
                if lesson.get("start") is not None and page_start is not None:
                    page_start = int(lesson["start"]) + int(page_start) - 1
                if lesson.get("start") is not None and page_end is not None:
                    page_end = int(lesson["start"]) + int(page_end) - 1
            except Exception:
                pass

            metadata = DocumentMetadata(
                sourceName=get_job(job_id).source_file,
                sourceUrl=None,
                originalFileName=chunk_pdf.name,
                mimeType=PDF_MIME,
                fileSizeBytes=int(storage_info.get("sizeBytes") or (chunk_pdf.stat().st_size if chunk_pdf.exists() else 0)),
                language="vi",
                collectedAt=now,
                licenseNote=None,
            )
            storage = StorageInfo(**storage_info)
            payload = {
                "map_id": document_id,
                "document_id": document_id,
                "title": title,
                "description": None,
                "keysearch": keysearch,
                "conceptMapId": concept_id,
                "concept_id": concept_id,
                "topic_id": topic_id,
                "typedocs": "pdf",
                "metadata": metadata.model_dump(mode="python"),
                "storage": storage.model_dump(mode="python"),
                "content": DocumentContent(summary=None).model_dump(mode="python"),
                "stemInfo": StemInfo().model_dump(mode="python"),
                "metadata_id": _metadata_id(document_id),
                "filePath": storage.objectKey,
                "content_preview": None,
                "order_index": _number_from_name(chunk_name),
                "page_start": page_start,
                "page_end": page_end,
                "status": "active",
                "createdBy": "AI_EXTRACT",
                "updatedBy": "AI_EXTRACT",
                "createdAt": existing.get("createdAt") if existing else now,
                "updatedAt": now,
            }
            doc = await self.documents.upsert_by_map_id(document_id, payload)
            sync = await safe_auto_sync("documents", document_id)
            persisted.append({"document_id": document_id, "mongo_id": doc.get("id"), "keysearch": keysearch, "filePath": storage.objectKey, "sync": sync})

        return {"entity": "documents", "lesson_name": lesson_name, "count": len(persisted), "items": persisted}
