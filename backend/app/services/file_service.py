from datetime import datetime, timezone
from typing import Any

from fastapi import UploadFile

from app.core.mongo import ensure_database_ready
from app.models.base import mongo_dump
from app.models.document_model import DocumentModel
from app.models.enums import EntityType
from app.models.storage import DocumentContent, DocumentMetadata, StemInfo, StorageInfo
from app.repositories.learning_repository import ConceptRepository, DocumentRepository, SubjectRepository, TopicRepository
from app.services.learning_service import LearningService
from app.services.storage_service import StorageService
from app.services.sync_service import safe_auto_sync
from app.utils.object_key import build_stem_object_key


class FileService:
    def __init__(self) -> None:
        self._storage: StorageService | None = None
        self.learning = LearningService()
        self.subjects = SubjectRepository()
        self.topics = TopicRepository()
        self.concepts = ConceptRepository()
        self.documents = DocumentRepository()

    @property
    def storage(self) -> StorageService:
        # Lazy init so the API can start even before Drive credentials are mounted.
        # Upload/download endpoints will raise a clear config error if Drive is not configured.
        if self._storage is None:
            self._storage = StorageService()
        return self._storage

    async def upload_entity_file(
        self,
        *,
        file: UploadFile,
        entity_type: EntityType,
        map_id: str,
    ) -> dict[str, Any]:
        await ensure_database_ready()

        if entity_type == EntityType.subjects:
            class_doc, entity = await self.learning.resolve_class_for_subject(map_id)
            repo = self.subjects
        elif entity_type == EntityType.topics:
            class_doc, entity = await self.learning.resolve_class_for_topic(map_id)
            repo = self.topics
        elif entity_type == EntityType.concepts:
            class_doc, entity = await self.learning.resolve_class_for_concept(map_id)
            repo = self.concepts
        else:
            raise ValueError("Use /upload-document for documents")

        object_key = build_stem_object_key(
            class_name=class_doc["name"],
            entity_type=entity_type,
            entity_name=entity["name"],
            original_filename=file.filename,
        )
        storage_data = await self.storage.upload_file(file=file, object_key=object_key)
        updated = await repo.update_by_map_id(map_id, {"filePath": object_key})
        sync_result = await safe_auto_sync(entity_type.value, map_id)
        return {
            "entityType": entity_type.value,
            "map_id": map_id,
            "className": class_doc["name"],
            "entityName": entity["name"],
            "filePath": object_key,
            "storage": StorageInfo(**storage_data).model_dump(),
            "updatedAt": updated.get("updatedAt") if updated else None,
            "sync": sync_result,
        }

    async def upload_document(
        self,
        *,
        file: UploadFile,
        map_id: str,
        title: str,
        conceptMapId: str,
        typedocs: str,
        metadata_id: str | None = None,
        description: str | None = None,
        keysearch: str | None = None,
        createdBy: str = "USER_001",
        updatedBy: str = "USER_001",
        sourceName: str | None = None,
        sourceUrl: str | None = None,
        language: str = "vi",
        licenseNote: str | None = None,
    ) -> dict[str, Any]:
        await ensure_database_ready()

        context = await self.learning.resolve_document_context(conceptMapId)
        class_doc = context["class"]

        object_key = build_stem_object_key(
            class_name=class_doc["name"],
            entity_type=EntityType.documents,
            entity_name=title,
            original_filename=file.filename,
        )
        storage_data = await self.storage.upload_file(file=file, object_key=object_key)
        now = datetime.now(timezone.utc)

        # Hiện tại chưa có auth bắt buộc. Nếu route truyền createdBy/updatedBy thì dùng giá trị đó,
        # nếu không thì fallback USER_001 để tương thích bản cũ.
        auto_user_id = createdBy or "USER_001"
        auto_updated_by = updatedBy or auto_user_id
        auto_language = language or "vi"

        model = DocumentModel(
            map_id=map_id,
            metadata_id=metadata_id,
            title=title,
            description=description,
            keysearch=keysearch,
            conceptMapId=conceptMapId,
            typedocs=typedocs,
            metadata=DocumentMetadata(
                sourceName=sourceName,
                sourceUrl=sourceUrl,
                originalFileName=file.filename or "uploaded-file",
                mimeType=file.content_type or "application/octet-stream",
                fileSizeBytes=storage_data.get("sizeBytes"),
                language=auto_language,
                collectedAt=now,
                licenseNote=licenseNote,
            ),
            storage=StorageInfo(**storage_data),
            content=DocumentContent(),
            stemInfo=StemInfo(),
            status="active",
            createdBy=auto_user_id,
            updatedBy=auto_updated_by,
            createdAt=now,
            updatedAt=now,
        )
        created = await self.documents.insert_one(mongo_dump(model))
        created["sync"] = await safe_auto_sync("documents", created["map_id"])
        return created

    async def get_document_download(self, map_id: str) -> dict[str, Any] | None:
        await ensure_database_ready()

        doc = await self.documents.find_by_map_id(map_id)
        if not doc:
            return None

        storage = doc.get("storage") or {}
        file_id = storage.get("fileId")
        if not file_id:
            raise ValueError("Document storage is missing Google Drive fileId")

        metadata = doc.get("metadata") or {}
        return {
            "stream": self.storage.download_file_to_memory(file_id),
            "filename": metadata.get("originalFileName") or storage.get("objectKey", "document-file").split("/")[-1],
            "mimeType": metadata.get("mimeType") or storage.get("mimeType") or "application/octet-stream",
        }

    async def get_presigned_document_url(self, map_id: str, expires_seconds: int = 3600) -> dict[str, Any] | None:
        """Compatibility method for the old /presigned-url route.

        Google Drive does not create MinIO-style presigned URLs. This returns
        the Drive view URL and useful Drive identifiers instead.
        """
        await ensure_database_ready()

        doc = await self.documents.find_by_map_id(map_id)
        if not doc:
            return None

        storage = doc.get("storage") or {}
        object_key = storage.get("objectKey")
        return {
            "objectKey": object_key,
            "provider": storage.get("provider", "google_drive"),
            "fileId": storage.get("fileId"),
            "url": self.storage.get_file_url(storage),
            "downloadUrl": storage.get("webContentLink"),
            "expiresSeconds": expires_seconds,
        }
