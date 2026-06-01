from __future__ import annotations

import re
import unicodedata
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
    TopicBagRepository,
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


def _slugify_keyword(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "keyword"


def _keyword_id(keyword_name: str) -> str:
    return f"KW_{_slugify_keyword(keyword_name)}"[:100]


def _split_keysearch_to_keyword_refs(keysearch: str | None) -> list[dict[str, Any]]:
    if not keysearch:
        return []
    normalized = re.sub(r"[;\n]+", ",", str(keysearch))
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in normalized.split(","):
        name = raw.strip()
        if not name:
            continue
        keyword_id = _keyword_id(name)
        if keyword_id in seen:
            continue
        seen.add(keyword_id)
        refs.append(
            {
                "keyword_id": keyword_id,
                "keyword_name": name,
                "normalized_name": _slugify_keyword(name),
                "aliases": [],
            }
        )
    return refs


def _embed_topic_bag_text(text: str) -> list[float]:
    if not text or not getattr(settings, "AUTO_EMBED_TOPIC_BAG", True):
        return []
    try:
        from embedding_utils import e5_embed_passage

        return e5_embed_passage(text)
    except Exception:
        return []




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
        self.topic_bags = TopicBagRepository()
        self.storage = StorageService()

    async def _set_metadata_id(self, repo: Any, map_id: str, doc: dict[str, Any]) -> dict[str, Any]:
        metadata_id = doc.get("id")
        if not metadata_id:
            return doc
        updated = await repo.update_by_map_id(map_id, {"metadata_id": str(metadata_id)})
        return updated or {**doc, "metadata_id": str(metadata_id)}

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
        subject_doc = await self._set_metadata_id(self.subjects, subject_id, subject_doc)
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
            doc = await self._set_metadata_id(self.topics, topic_id, doc)
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
                    "name": lesson_title,
                    "definition": None,
                    "conceptNumber": _number_from_name(lesson_id),
                    "filePath": file_path,
                },
            )
            doc = await self._set_metadata_id(self.concepts, lesson_id, doc)
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
        """Load all chunks for a lesson without dropping any chunk.

        Earlier versions preferred chunks_approved.json exclusively. If that file was
        incomplete while individual chunk_*.json files were complete, one chunk could
        be missed during persistence. This method merges both sources by chunk.name,
        giving approved data priority but filling any missing chunks from individual
        files.
        """
        lesson_dir = get_chunk_lesson_dir(job_id, lesson_name)
        chunk_by_name: dict[str, dict[str, Any]] = {}

        # First read individual files so they act as a complete fallback source.
        for path in sorted(lesson_dir.glob("chunk_*.json")):
            payload = read_json(path)
            if isinstance(payload, dict):
                name = str(payload.get("name") or path.stem).strip()
                if name:
                    payload.setdefault("name", name)
                    chunk_by_name[name] = payload

        # Then overlay the reviewed/approved version when present.
        approved_path = lesson_dir / "chunks_approved.json"
        if approved_path.exists():
            payload = read_json(approved_path)
            chunks = payload.get("chunks") if isinstance(payload, dict) else None
            if isinstance(chunks, list):
                for chunk in chunks:
                    if not isinstance(chunk, dict):
                        continue
                    name = str(chunk.get("name") or "").strip()
                    if name:
                        chunk_by_name[name] = chunk

        return sorted(
            chunk_by_name.values(),
            key=lambda item: (_number_from_name(str(item.get("name") or "")) or 10**9, str(item.get("name") or "")),
        )

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

    async def _get_lesson_context(
        self,
        *,
        job_id: str,
        lesson_name: str,
    ) -> tuple[dict[str, Any], str, str, str, str]:
        """Return lesson, concept_id, topic_id, class_name and source file.

        This helper keeps finalize persistence and keyword persistence aligned.
        """
        job = get_job(job_id)
        lesson = self._load_lesson(job_id=job_id, lesson_name=lesson_name)
        concept_id = str(lesson.get("name") or lesson_name)
        topic_id = str(lesson.get("topic_name") or "").strip()
        if not topic_id:
            raise ExtractPersistenceError(f"Lesson {lesson_name!r} has no topic_name.")

        concept_doc = await self.concepts.find_by_map_id(concept_id)
        if not concept_doc:
            # This keeps the route usable if the caller forgot to approve-lessons persistence.
            await self.persist_lessons(job_id=job_id)
            concept_doc = await self.concepts.find_by_map_id(concept_id)
        if not concept_doc:
            raise ExtractPersistenceError(f"Concept {concept_id!r} was not found.")

        topic_doc = await self.topics.find_by_map_id(topic_id)
        if not topic_doc:
            raise ExtractPersistenceError(f"Topic {topic_id!r} must be persisted before documents.")

        subject_ref = str(topic_doc.get("subjectMapId") or topic_doc.get("subject_id") or "")
        subject_doc = await self.subjects.find_by_map_id(subject_ref) if subject_ref else None
        class_ref = str(subject_doc.get("classMapId") or subject_doc.get("class_id") or "") if subject_doc else ""
        class_doc = await self.classes.find_by_map_id(class_ref) if class_ref else None
        if not class_doc:
            raise ExtractPersistenceError(f"Class context for topic {topic_id!r} was not found.")

        class_name = str(class_doc.get("name") or class_doc.get("section") or class_doc.get("map_id") or "class")
        return lesson, concept_id, topic_id, class_name, job.source_file

    def _chunk_page_range(self, *, lesson: dict[str, Any], chunk: dict[str, Any]) -> tuple[Any, Any]:
        page_start = chunk.get("start")
        page_end = chunk.get("end")
        try:
            if lesson.get("start") is not None and page_start is not None:
                page_start = int(lesson["start"]) + int(page_start) - 1
            if lesson.get("start") is not None and page_end is not None:
                page_end = int(lesson["start"]) + int(page_end) - 1
        except Exception:
            pass
        return page_start, page_end

    async def _build_document_payload(
        self,
        *,
        job_id: str,
        lesson_name: str,
        lesson: dict[str, Any],
        concept_id: str,
        topic_id: str,
        class_name: str,
        source_file: str,
        chunk: dict[str, Any],
        upload_document: bool,
        apply_keywords: bool,
    ) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
        chunk_name = str(chunk.get("name") or "").strip()
        if not chunk_name:
            raise ExtractPersistenceError("Chunk has no name.")

        document_id = _doc_id(lesson_name, chunk_name)
        title = _clean_title(chunk.get("heading"), chunk.get("title")) or document_id
        chunk_pdf = get_chunk_pdf_path(job_id, lesson_name, chunk_name)
        if upload_document and not chunk_pdf.exists():
            raise FileNotFoundError(f"Chunk PDF was not found: {chunk_pdf}")

        existing = await self.documents.find_by_map_id(document_id)
        existing_storage = existing.get("storage") if existing else None
        storage_info = existing_storage
        uploaded_storage = None

        if upload_document:
            storage_info = await self._upload_pdf(
                class_name=class_name,
                entity_type=EntityType.documents,
                entity_name=title,
                pdf_path=chunk_pdf,
            )
            uploaded_storage = storage_info

        if not storage_info:
            raise ExtractPersistenceError(
                f"Document {document_id!r} has no storage info. Run finalize persistence before syncing keywords."
            )

        keyword_by_chunk = self._load_keyword_results(job_id=job_id, lesson_name=lesson_name) if apply_keywords else {}
        keyword_result = keyword_by_chunk.get(chunk_name)
        keysearch = _keysearch_from_result(keyword_result) if apply_keywords else (existing.get("keysearch") if existing else None)
        page_start, page_end = self._chunk_page_range(lesson=lesson, chunk=chunk)
        now = datetime.now(timezone.utc)

        metadata = DocumentMetadata(
            sourceName=source_file,
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
            "typedocs": "pdf",
            "metadata": metadata.model_dump(mode="python"),
            "storage": storage.model_dump(mode="python"),
            "content": DocumentContent(summary=None).model_dump(mode="python"),
            "stemInfo": StemInfo().model_dump(mode="python"),
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
        return document_id, payload, uploaded_storage

    async def _sync_document_checked(self, document_id: str) -> dict[str, Any]:
        """Sync one document and fail loudly when sync fails.

        safe_auto_sync is still used so one bad document does not interrupt the
        processing loop before the remaining documents are attempted, but the caller
        receives enough detail to know exactly which document failed.
        """
        result = await safe_auto_sync("documents", document_id)
        if not result or result.get("ok") is False:
            error = result.get("error") if isinstance(result, dict) else result
            raise ExtractPersistenceError(f"Sync failed for document {document_id!r}: {error}")
        return result

    async def _persist_documents_for_lesson(
        self,
        *,
        job_id: str,
        lesson_name: str,
        upload_document: bool,
        apply_keywords: bool,
        stage: str,
    ) -> dict[str, Any]:
        lesson, concept_id, topic_id, class_name, source_file = await self._get_lesson_context(
            job_id=job_id,
            lesson_name=lesson_name,
        )
        chunks = self._load_chunks(job_id=job_id, lesson_name=lesson_name)
        persisted: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for chunk in chunks:
            if not isinstance(chunk, dict) or not str(chunk.get("name") or "").strip():
                continue
            try:
                document_id, payload, uploaded_storage = await self._build_document_payload(
                    job_id=job_id,
                    lesson_name=lesson_name,
                    lesson=lesson,
                    concept_id=concept_id,
                    topic_id=topic_id,
                    class_name=class_name,
                    source_file=source_file,
                    chunk=chunk,
                    upload_document=upload_document,
                    apply_keywords=apply_keywords,
                )
                doc = await self.documents.upsert_by_map_id(document_id, payload)
                doc = await self._set_metadata_id(self.documents, document_id, doc)
                sync = await self._sync_document_checked(document_id)
                persisted.append(
                    {
                        "document_id": document_id,
                        "mongo_id": doc.get("id"),
                        "filePath": payload.get("filePath"),
                        "keysearch": payload.get("keysearch"),
                        "storage": uploaded_storage,
                        "sync": sync,
                    }
                )
            except Exception as exc:
                errors.append(
                    {
                        "chunk_name": str(chunk.get("name") or ""),
                        "document_id": _doc_id(lesson_name, str(chunk.get("name") or "")),
                        "error": str(exc),
                    }
                )

        if errors:
            raise ExtractPersistenceError(
                f"Failed to persist/sync {len(errors)} document(s) for lesson {lesson_name!r}: {errors}"
            )

        return {
            "entity": "documents",
            "stage": stage,
            "lesson_name": lesson_name,
            "count": len(persisted),
            "items": persisted,
        }

    async def persist_approved_documents(
        self,
        *,
        job_id: str,
        lesson_name: str,
    ) -> dict[str, Any]:
        """Persist reviewed chunk PDFs immediately after chunk approval.

        This creates/syncs DOCUMENT, DOC_CONCEPT and DOC_TYPE as soon as the user
        approves chunks. If finalize is run later, persist_finalized_documents will
        overwrite the same document_id records with finalized PDF storage metadata.
        """
        result = await self._persist_documents_for_lesson(
            job_id=job_id,
            lesson_name=lesson_name,
            upload_document=True,
            apply_keywords=False,
            stage="chunks_approved",
        )
        result["note"] = "Approved chunk PDFs were persisted as documents. Finalize will overwrite the same documents with finalized PDFs."
        return result

    async def persist_finalized_documents(
        self,
        *,
        job_id: str,
        lesson_name: str,
    ) -> dict[str, Any]:
        """Persist finalized chunk PDFs as DOCUMENT records.

        This is called by /chunks/.../finalize. It overwrites the same document_id
        records created at chunk approval time, but still does not create/update
        keyword-derived data.
        """
        result = await self._persist_documents_for_lesson(
            job_id=job_id,
            lesson_name=lesson_name,
            upload_document=True,
            apply_keywords=False,
            stage="finalize",
        )
        result["note"] = "Finalized chunk PDFs overwrote document storage. Keywords/keysearch are synced after keyword approval."
        return result

    async def _rebuild_mongo_topic_bag(self, *, topic_id: str) -> dict[str, Any]:
        """Rebuild MongoDB topic_bags from keyword names only.

        TopicBag is intentionally kept only in MongoDB. PostgreSQL and Neo4j do
        not receive TopicBag. The embedding_text must be built from keyword_name
        values, not from topic/document/chunk titles.
        """
        concept_ids: list[str] = []
        async for concept in self.concepts.collection.find({"topicMapId": topic_id}):
            concept_id = str(concept.get("map_id") or concept.get("concept_id") or "").strip()
            if concept_id and concept_id not in concept_ids:
                concept_ids.append(concept_id)

        cursor = self.documents.collection.find({"conceptMapId": {"$in": concept_ids}})
        document_ids: list[str] = []
        keyword_refs_by_id: dict[str, dict[str, Any]] = {}

        async for document in cursor:
            document_id = str(document.get("map_id") or document.get("document_id") or "").strip()
            if document_id and document_id not in document_ids:
                document_ids.append(document_id)

            for keyword_ref in _split_keysearch_to_keyword_refs(document.get("keysearch")):
                keyword_id = str(keyword_ref.get("keyword_id") or "").strip()
                if keyword_id and keyword_id not in keyword_refs_by_id:
                    keyword_refs_by_id[keyword_id] = keyword_ref

        keyword_refs = list(keyword_refs_by_id.values())
        keyword_names = [str(item.get("keyword_name") or "").strip() for item in keyword_refs]
        keyword_names = [name for name in keyword_names if name]
        embedding_text = " | ".join(keyword_names)
        topic_bag_id = f"TB_{topic_id}"[:100]
        now = datetime.now(timezone.utc)

        payload = {
            "map_id": topic_bag_id,
            "topic_bag_id": topic_bag_id,
            "topic_id": topic_id,
            "owner_type": "topic",
            "owner_id": topic_id,
            "document_ids": document_ids,
            "keyword_refs": keyword_refs,
            "embedding_text": embedding_text,
            "embedding_model": getattr(settings, "EMBEDDING_MODEL", "manual-keyword-topic-bag"),
            "embedding": _embed_topic_bag_text(embedding_text),
            "updatedBy": "AI_EXTRACT",
            "updatedAt": now,
        }

        existing = await self.topic_bags.collection.find_one({"topic_id": topic_id})
        if existing and existing.get("createdAt") is not None:
            payload["createdAt"] = existing.get("createdAt")
        else:
            payload["createdAt"] = now
            payload["createdBy"] = "AI_EXTRACT"

        await self.topic_bags.collection.update_one({"topic_id": topic_id}, {"$set": payload}, upsert=True)
        saved = await self.topic_bags.collection.find_one({"topic_id": topic_id})
        return {
            "topic_bag_id": topic_bag_id,
            "topic_id": topic_id,
            "document_count": len(document_ids),
            "keyword_count": len(keyword_refs),
            "embedding_text": embedding_text,
            "mongo_id": str(saved.get("_id")) if saved else None,
        }


    async def persist_approved_keywords(
        self,
        *,
        job_id: str,
        lesson_name: str,
    ) -> dict[str, Any]:
        """Persist approved keyword data onto existing DOCUMENT records.

        This is called by /keywords/.../approve.
        It updates DOCUMENT.keysearch and lets the sync layer create MongoDB
        keywords/document_keywords plus Neo4j Keyword nodes from that keysearch.
        PostgreSQL no longer stores keyword tables.
        """
        lesson, concept_id, topic_id, class_name, source_file = await self._get_lesson_context(
            job_id=job_id,
            lesson_name=lesson_name,
        )
        approved_keywords_path = get_keywords_approved_json_path(job_id, lesson_name)
        if not approved_keywords_path.exists():
            raise FileNotFoundError("Approved lesson keywords JSON was not found.")

        chunks = self._load_chunks(job_id=job_id, lesson_name=lesson_name)
        keyword_by_chunk = self._load_keyword_results(job_id=job_id, lesson_name=lesson_name)
        if not keyword_by_chunk:
            raise ExtractPersistenceError(f"No approved keyword results were found for lesson {lesson_name!r}.")

        persisted: list[dict[str, Any]] = []
        for chunk in chunks:
            if not isinstance(chunk, dict) or not str(chunk.get("name") or "").strip():
                continue
            chunk_name = str(chunk.get("name") or "").strip()
            document_id = _doc_id(lesson_name, chunk_name)
            if chunk_name not in keyword_by_chunk:
                raise ExtractPersistenceError(
                    f"Missing approved keywords for {lesson_name}/{chunk_name}. Extract/review all chunk keywords before approve."
                )

            document_id, payload, _uploaded_storage = await self._build_document_payload(
                job_id=job_id,
                lesson_name=lesson_name,
                lesson=lesson,
                concept_id=concept_id,
                topic_id=topic_id,
                class_name=class_name,
                source_file=source_file,
                chunk=chunk,
                upload_document=False,
                apply_keywords=True,
            )
            doc = await self.documents.upsert_by_map_id(document_id, payload)
            doc = await self._set_metadata_id(self.documents, document_id, doc)
            sync = await self._sync_document_checked(document_id)
            persisted.append(
                {
                    "document_id": document_id,
                    "mongo_id": doc.get("id"),
                    "filePath": payload.get("filePath"),
                    "keysearch": payload.get("keysearch"),
                    "sync": sync,
                }
            )

        topic_bag = await self._rebuild_mongo_topic_bag(topic_id=topic_id)

        return {
            "entity": "documents_keywords",
            "stage": "keywords_approved",
            "lesson_name": lesson_name,
            "count": len(persisted),
            "items": persisted,
            "topic_bag": topic_bag,
            "note": "Approved keywords were synced into document.keysearch, MongoDB keywords/document_keywords, and Neo4j Keyword nodes. MongoDB topic_bag was rebuilt from keyword_name values only.",
        }

    async def persist_lesson_documents(
        self,
        *,
        job_id: str,
        lesson_name: str,
        upload_documents: bool = True,
    ) -> dict[str, Any]:
        """Backward-compatible wrapper.

        Older route code called persist_lesson_documents(upload_documents=True) after finalize and
        persist_lesson_documents(upload_documents=False) after keyword approval. Keep the method so
        old callers still work, but route code should prefer the explicit methods above.
        """
        if upload_documents:
            return await self.persist_finalized_documents(job_id=job_id, lesson_name=lesson_name)
        return await self.persist_approved_keywords(job_id=job_id, lesson_name=lesson_name)
