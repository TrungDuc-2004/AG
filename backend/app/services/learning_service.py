from typing import Any

from app.models.base import mongo_dump
from app.models.class_model import ClassModel
from app.models.concept_model import ConceptModel
from app.models.document_model import DocumentModel
from app.models.subject_model import SubjectModel
from app.models.topic_model import TopicModel
from app.models.user_model import UserModel
from app.repositories.learning_repository import (
    ClassRepository,
    ConceptRepository,
    DocumentRepository,
    SubjectRepository,
    TopicRepository,
    UserRepository,
)
from app.services.sync_service import safe_auto_sync


class LearningService:
    def __init__(self) -> None:
        self.classes = ClassRepository()
        self.subjects = SubjectRepository()
        self.topics = TopicRepository()
        self.concepts = ConceptRepository()
        self.documents = DocumentRepository()
        self.users = UserRepository()

    async def _set_metadata_id(self, repo, created: dict[str, Any]) -> dict[str, Any]:
        metadata_id = created.get("id")
        map_id = created.get("map_id")
        if not metadata_id or not map_id:
            return created
        updated = await repo.update_by_map_id(str(map_id), {"metadata_id": str(metadata_id)})
        return updated or {**created, "metadata_id": str(metadata_id)}

    async def create_class(self, data: dict[str, Any]) -> dict[str, Any]:
        model = ClassModel(**data)
        created = await self.classes.insert_one(mongo_dump(model))
        created["sync"] = await safe_auto_sync("classes", created["map_id"])
        return created

    async def create_subject(self, data: dict[str, Any]) -> dict[str, Any]:
        if not await self.classes.find_by_map_id(data["classMapId"]):
            raise ValueError("classMapId does not exist")
        model = SubjectModel(**data)
        created = await self.subjects.insert_one(mongo_dump(model))
        created = await self._set_metadata_id(self.subjects, created)
        created["sync"] = await safe_auto_sync("subjects", created["map_id"])
        return created

    async def create_topic(self, data: dict[str, Any]) -> dict[str, Any]:
        if not await self.subjects.find_by_map_id(data["subjectMapId"]):
            raise ValueError("subjectMapId does not exist")
        model = TopicModel(**data)
        created = await self.topics.insert_one(mongo_dump(model))
        created = await self._set_metadata_id(self.topics, created)
        created["sync"] = await safe_auto_sync("topics", created["map_id"])
        return created

    async def create_concept(self, data: dict[str, Any]) -> dict[str, Any]:
        if not await self.topics.find_by_map_id(data["topicMapId"]):
            raise ValueError("topicMapId does not exist")
        model = ConceptModel(**data)
        created = await self.concepts.insert_one(mongo_dump(model))
        created = await self._set_metadata_id(self.concepts, created)
        created["sync"] = await safe_auto_sync("concepts", created["map_id"])
        return created

    async def create_document(self, data: dict[str, Any]) -> dict[str, Any]:
        if not await self.concepts.find_by_map_id(data["conceptMapId"]):
            raise ValueError("conceptMapId does not exist")
        model = DocumentModel(**data)
        created = await self.documents.insert_one(mongo_dump(model))
        created = await self._set_metadata_id(self.documents, created)
        created["sync"] = await safe_auto_sync("documents", created["map_id"])
        return created

    async def create_user(self, data: dict[str, Any]) -> dict[str, Any]:
        model = UserModel(**data)
        created = await self.users.insert_one(mongo_dump(model))
        created["sync"] = await safe_auto_sync("users", created["map_id"])
        return created

    async def resolve_class_for_subject(self, subject_map_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        subject = await self.subjects.find_by_map_id(subject_map_id)
        if not subject:
            raise ValueError("Subject not found")
        class_doc = await self.classes.find_by_map_id(subject["classMapId"])
        if not class_doc:
            raise ValueError("Class of subject not found")
        return class_doc, subject

    async def resolve_class_for_topic(self, topic_map_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        topic = await self.topics.find_by_map_id(topic_map_id)
        if not topic:
            raise ValueError("Topic not found")
        class_doc, _subject = await self.resolve_class_for_subject(topic["subjectMapId"])
        return class_doc, topic

    async def resolve_class_for_concept(self, concept_map_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        concept = await self.concepts.find_by_map_id(concept_map_id)
        if not concept:
            raise ValueError("Concept not found")
        class_doc, _topic = await self.resolve_class_for_topic(concept["topicMapId"])
        return class_doc, concept

    async def resolve_document_context(self, concept_map_id: str) -> dict[str, Any]:
        concept = await self.concepts.find_by_map_id(concept_map_id)
        if not concept:
            raise ValueError("Concept not found")
        topic = await self.topics.find_by_map_id(concept["topicMapId"])
        if not topic:
            raise ValueError("Topic not found")
        subject = await self.subjects.find_by_map_id(topic["subjectMapId"])
        if not subject:
            raise ValueError("Subject not found")
        class_doc = await self.classes.find_by_map_id(subject["classMapId"])
        if not class_doc:
            raise ValueError("Class not found")
        return {
            "class": class_doc,
            "subject": subject,
            "topic": topic,
            "concept": concept,
        }
