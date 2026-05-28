import json
import re
import unicodedata
from datetime import date, datetime, timezone
from typing import Any

import asyncpg
from neo4j import AsyncDriver

from app.core.config import settings
from app.core.mongo import ensure_database_ready, get_database
from app.core.neo4j import ensure_neo4j_ready, get_neo4j_driver, neo4j_health
from app.core.postgres import ensure_postgres_ready, get_pg_pool, postgres_health
from app.repositories.learning_repository import (
    ClassRepository,
    ConceptRepository,
    DocumentRepository,
    SubjectRepository,
    TopicRepository,
    UserRepository,
)

TYPEDOC_LABELS = {
    "1": "document",
    "2": "image",
    "3": "video",
}

ROLE_LABELS = {
    "1": "admin",
    "2": "user",
    "3": "giáo viên",
    "admin": "admin",
    "user": "user",
    "teacher": "giáo viên",
    "giáo viên": "giáo viên",
}


def _string_id(value: Any, fallback: str | None = None) -> str:
    raw = value if value not in (None, "") else fallback
    if raw in (None, ""):
        raise ValueError("Missing required id")
    return str(raw)[:100]


def _doc_business_id(doc: dict[str, Any], field: str) -> str:
    return _string_id(doc.get(field) or doc.get("map_id"))


def _class_id(doc: dict[str, Any]) -> str:
    return _doc_business_id(doc, "class_id")


def _subject_id(doc: dict[str, Any]) -> str:
    return _doc_business_id(doc, "subject_id")


def _topic_id(doc: dict[str, Any]) -> str:
    return _doc_business_id(doc, "topic_id")


def _concept_id(doc: dict[str, Any]) -> str:
    return _doc_business_id(doc, "concept_id")


def _document_id(doc: dict[str, Any]) -> str:
    return _doc_business_id(doc, "document_id")


def _user_id(doc: dict[str, Any]) -> str:
    return _doc_business_id(doc, "user_id")


def _parse_grade(class_doc: dict[str, Any]) -> int | None:
    raw = str(class_doc.get("grade") or class_doc.get("map_id") or class_doc.get("name") or "")
    match = re.search(r"\d+", raw)
    return int(match.group()) if match else None


def _to_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "keyword"


def _keyword_id(keyword_name: str) -> str:
    return f"KW_{_slugify(keyword_name)}"[:100]


def _split_keywords(keysearch: str | None) -> list[dict[str, Any]]:
    if not keysearch:
        return []
    normalized = re.sub(r"[;\n]+", ",", str(keysearch))
    seen: set[str] = set()
    keywords: list[dict[str, Any]] = []
    for raw in normalized.split(","):
        name = raw.strip()
        if not name:
            continue
        kid = _keyword_id(name)
        if kid in seen:
            continue
        seen.add(kid)
        keywords.append(
            {
                "keyword_id": kid,
                "keyword_name": name,
                "normalized_name": _slugify(name),
                "aliases": [],
            }
        )
    return keywords


def _jsonb(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _storage_object_key(document_doc: dict[str, Any]) -> str | None:
    storage = document_doc.get("storage") or {}
    return storage.get("objectKey") or document_doc.get("filePath")


def _metadata_id(document_doc: dict[str, Any]) -> str:
    return str(document_doc.get("metadata_id") or f"META_{_document_id(document_doc)}")[:255]


def _content_preview(document_doc: dict[str, Any]) -> str | None:
    content = document_doc.get("content") or {}
    return document_doc.get("content_preview") or content.get("summary") or document_doc.get("description")


class SyncService:
    """Sync MongoDB metadata to PostgreSQL and Neo4j.

    Target schema follows the provided migration files:
    - PostgreSQL IDs are VARCHAR(100), using the app's map_id as the business ID.
    - MongoDB remains the source of truth.
    - Neo4j receives Subject/Topic/Concept/Document/Keyword nodes. TopicBag and TypeDoc are not synced to Neo4j.
    """

    def __init__(self) -> None:
        self.classes = ClassRepository()
        self.subjects = SubjectRepository()
        self.topics = TopicRepository()
        self.concepts = ConceptRepository()
        self.documents = DocumentRepository()
        self.users = UserRepository()

    async def ensure_targets_ready(self) -> None:
        await ensure_database_ready()
        await ensure_postgres_ready()
        await ensure_neo4j_ready()

    async def health(self) -> dict[str, Any]:
        return {
            "postgres": await postgres_health(),
            "neo4j": await neo4j_health(),
        }

    async def check_mongo_compatibility(self) -> dict[str, Any]:
        await ensure_database_ready()
        db = get_database()
        collections = set(await db.list_collection_names())
        required = {
            "classes",
            "subjects",
            "topics",
            "concepts",
            "documents",
            "users",
            "roles",
            "typedocs",
            "keywords",
            "document_keywords",
            "document_metadata",
            "class_subjects",
            "doc_concepts",
            "doc_types",
            "logs",
        }
        missing_collections = sorted(required - collections)
        counts = {name: await db[name].count_documents({}) for name in sorted(required & collections)}
        issues: list[str] = []

        async for subject in db.subjects.find({}):
            if not (subject.get("map_id") or subject.get("subject_id")):
                issues.append("Subject thiếu map_id/subject_id")
            if not (subject.get("classMapId") or subject.get("class_id")):
                issues.append(f"Subject {subject.get('map_id')} thiếu classMapId/class_id")

        async for topic in db.topics.find({}):
            if not (topic.get("map_id") or topic.get("topic_id")):
                issues.append("Topic thiếu map_id/topic_id")
            if not (topic.get("subjectMapId") or topic.get("subject_id")):
                issues.append(f"Topic {topic.get('map_id')} thiếu subjectMapId/subject_id")

        async for concept in db.concepts.find({}):
            if not (concept.get("map_id") or concept.get("concept_id")):
                issues.append("Concept thiếu map_id/concept_id")
            if not (concept.get("topicMapId") or concept.get("topic_id")):
                issues.append(f"Concept {concept.get('map_id')} thiếu topicMapId/topic_id")

        async for document in db.documents.find({}):
            if not (document.get("map_id") or document.get("document_id")):
                issues.append("Document thiếu map_id/document_id")
            if not document.get("conceptMapId"):
                issues.append(f"Document {document.get('map_id')} thiếu conceptMapId")
            if not _storage_object_key(document):
                issues.append(f"Document {document.get('map_id')} thiếu file_path/storage.objectKey")

        return {
            "ok": not missing_collections and not issues,
            "requiredCollections": sorted(required),
            "missingCollections": missing_collections,
            "counts": counts,
            "issues": issues,
            "note": "Startup now auto-creates Mongo collections, PostgreSQL tables and Neo4j constraints.",
        }

    # ---------- Mongo auxiliary upserts ----------

    async def _mongo_upsert_aux(self, collection_name: str, key: dict[str, Any], data: dict[str, Any]) -> None:
        db = get_database()
        now = datetime.now(timezone.utc)
        payload = {**key, **data, "updatedAt": now}
        await db[collection_name].update_one(
            key,
            {"$set": payload, "$setOnInsert": {"createdAt": now}},
            upsert=True,
        )

    async def _mongo_upsert_document_metadata(self, document_doc: dict[str, Any]) -> str:
        document_id = _document_id(document_doc)
        metadata_id = _metadata_id(document_doc)
        await self._mongo_upsert_aux(
            "document_metadata",
            {"document_id": document_id},
            {
                "metadata_id": metadata_id,
                "metadata": document_doc.get("metadata") or {},
            },
        )
        return metadata_id

    # ---------- PostgreSQL upsert helpers ----------

    async def _pg_upsert_class(self, conn: asyncpg.Connection, class_doc: dict[str, Any]) -> asyncpg.Record:
        class_id = _class_id(class_doc)
        return await conn.fetchrow(
            """
            INSERT INTO CLASS (class_id, grade, section)
            VALUES ($1, $2, $3)
            ON CONFLICT (class_id) DO UPDATE SET
                grade = EXCLUDED.grade,
                section = EXCLUDED.section,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            class_id,
            _parse_grade(class_doc),
            class_doc.get("section") or class_doc.get("name"),
        )

    async def _pg_upsert_subject(self, conn: asyncpg.Connection, subject_doc: dict[str, Any]) -> asyncpg.Record:
        subject_id = _subject_id(subject_doc)
        class_ref = subject_doc.get("classMapId") or subject_doc.get("class_id")
        if not class_ref:
            raise ValueError(f"Subject {subject_id} missing classMapId/class_id")
        class_doc = await self.classes.find_by_map_id(str(class_ref))
        if not class_doc:
            raise ValueError(f"Class not found for subject {subject_id}")
        pg_class = await self._pg_upsert_class(conn, class_doc)
        row = await conn.fetchrow(
            """
            INSERT INTO SUBJECT (subject_id, name, description)
            VALUES ($1, $2, $3)
            ON CONFLICT (subject_id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            subject_id,
            subject_doc.get("name"),
            subject_doc.get("description"),
        )
        await conn.execute(
            """
            INSERT INTO CLASS_SUBJECT (class_id, subject_id)
            VALUES ($1, $2)
            ON CONFLICT (class_id, subject_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            """,
            pg_class["class_id"],
            row["subject_id"],
        )
        await self._mongo_upsert_aux(
            "class_subjects",
            {"class_id": pg_class["class_id"], "subject_id": row["subject_id"]},
            {},
        )
        return row

    async def _pg_upsert_topic(self, conn: asyncpg.Connection, topic_doc: dict[str, Any]) -> asyncpg.Record:
        topic_id = _topic_id(topic_doc)
        subject_ref = topic_doc.get("subjectMapId") or topic_doc.get("subject_id")
        if not subject_ref:
            raise ValueError(f"Topic {topic_id} missing subjectMapId/subject_id")
        subject_doc = await self.subjects.find_by_map_id(str(subject_ref))
        if not subject_doc:
            raise ValueError(f"Subject not found for topic {topic_id}")
        pg_subject = await self._pg_upsert_subject(conn, subject_doc)
        return await conn.fetchrow(
            """
            INSERT INTO TOPIC (topic_id, subject_id, name)
            VALUES ($1, $2, $3)
            ON CONFLICT (topic_id) DO UPDATE SET
                subject_id = EXCLUDED.subject_id,
                name = EXCLUDED.name,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            topic_id,
            pg_subject["subject_id"],
            topic_doc.get("name"),
        )

    async def _pg_upsert_concept(self, conn: asyncpg.Connection, concept_doc: dict[str, Any]) -> asyncpg.Record:
        concept_id = _concept_id(concept_doc)
        topic_ref = concept_doc.get("topicMapId") or concept_doc.get("topic_id")
        if not topic_ref:
            raise ValueError(f"Concept {concept_id} missing topicMapId/topic_id")
        topic_doc = await self.topics.find_by_map_id(str(topic_ref))
        if not topic_doc:
            raise ValueError(f"Topic not found for concept {concept_id}")
        pg_topic = await self._pg_upsert_topic(conn, topic_doc)
        return await conn.fetchrow(
            """
            INSERT INTO CONCEPT (concept_id, topic_id, name, definition, file_path)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (concept_id) DO UPDATE SET
                topic_id = EXCLUDED.topic_id,
                name = EXCLUDED.name,
                definition = EXCLUDED.definition,
                file_path = EXCLUDED.file_path,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            concept_id,
            pg_topic["topic_id"],
            concept_doc.get("name"),
            concept_doc.get("definition"),
            concept_doc.get("filePath") or concept_doc.get("file_path"),
        )

    async def _pg_upsert_role(self, conn: asyncpg.Connection, role_value: str | None) -> asyncpg.Record:
        role_id = _string_id(role_value or "2")
        name = ROLE_LABELS.get(role_id, role_id)
        row = await conn.fetchrow(
            """
            INSERT INTO ROLES (role_id, name, description)
            VALUES ($1, $2, $3)
            ON CONFLICT (role_id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            role_id,
            name,
            "Auto-created from MongoDB users.role field",
        )
        await self._mongo_upsert_aux(
            "roles",
            {"role_id": role_id},
            {"name": name, "description": "Auto-created from MongoDB users.role field"},
        )
        return row

    async def _pg_upsert_user(self, conn: asyncpg.Connection, user_doc: dict[str, Any]) -> asyncpg.Record:
        user_id = _user_id(user_doc)
        role = await self._pg_upsert_role(conn, user_doc.get("role"))
        return await conn.fetchrow(
            """
            INSERT INTO "USER" (user_id, name, birth_date, role_id)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO UPDATE SET
                name = EXCLUDED.name,
                birth_date = EXCLUDED.birth_date,
                role_id = EXCLUDED.role_id,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            user_id,
            user_doc.get("name"),
            _to_date(user_doc.get("birthDate") or user_doc.get("birth_date")),
            role["role_id"],
        )

    async def _pg_upsert_typedoc(self, conn: asyncpg.Connection, typedocs: str | None) -> asyncpg.Record | None:
        if not typedocs:
            return None
        typedoc_id = _string_id(typedocs)
        name = TYPEDOC_LABELS.get(typedoc_id, typedoc_id)
        row = await conn.fetchrow(
            """
            INSERT INTO TYPEDOC (typedoc_id, name, description)
            VALUES ($1, $2, $3)
            ON CONFLICT (typedoc_id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            typedoc_id,
            name,
            "Auto-created from MongoDB documents.typedocs field",
        )
        await self._mongo_upsert_aux(
            "typedocs",
            {"typedoc_id": typedoc_id},
            {"name": name, "description": "Auto-created from MongoDB documents.typedocs field"},
        )
        return row

    async def _pg_upsert_keyword(self, conn: asyncpg.Connection, keyword: dict[str, Any]) -> asyncpg.Record:
        row = await conn.fetchrow(
            """
            INSERT INTO KEYWORD (keyword_id, keyword_name, normalized_name, aliases)
            VALUES ($1, $2, $3, $4::jsonb)
            ON CONFLICT (keyword_id) DO UPDATE SET
                keyword_name = EXCLUDED.keyword_name,
                normalized_name = EXCLUDED.normalized_name,
                aliases = EXCLUDED.aliases,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            keyword["keyword_id"],
            keyword["keyword_name"],
            keyword["normalized_name"],
            _jsonb(keyword.get("aliases", [])),
        )
        await self._mongo_upsert_aux("keywords", {"keyword_id": keyword["keyword_id"]}, keyword)
        return row

    async def _pg_link_document_keyword(
        self,
        conn: asyncpg.Connection,
        document_id: str,
        keyword_id: str,
    ) -> None:
        await conn.execute(
            """
            INSERT INTO DOCUMENT_KEYWORD (document_id, keyword_id)
            VALUES ($1, $2)
            ON CONFLICT (document_id, keyword_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            """,
            document_id,
            keyword_id,
        )
        await self._mongo_upsert_aux(
            "document_keywords",
            {"document_id": document_id, "keyword_id": keyword_id},
            {},
        )

    async def _pg_upsert_document(self, conn: asyncpg.Connection, document_doc: dict[str, Any]) -> asyncpg.Record:
        document_id = _document_id(document_doc)
        concept_ref = document_doc.get("conceptMapId") or document_doc.get("concept_id")
        if not concept_ref:
            raise ValueError(f"Document {document_id} missing conceptMapId/concept_id")
        concept_doc = await self.concepts.find_by_map_id(str(concept_ref))
        if not concept_doc:
            raise ValueError(f"Concept not found for document {document_id}")
        pg_concept = await self._pg_upsert_concept(conn, concept_doc)
        topic_id = pg_concept["topic_id"]
        metadata_id = await self._mongo_upsert_document_metadata(document_doc)
        row = await conn.fetchrow(
            """
            INSERT INTO DOCUMENT (
                document_id, title, file_path, keysearch, topic_id, metadata_id,
                content_preview, order_index, page_start, page_end
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (document_id) DO UPDATE SET
                title = EXCLUDED.title,
                file_path = EXCLUDED.file_path,
                keysearch = EXCLUDED.keysearch,
                topic_id = EXCLUDED.topic_id,
                metadata_id = EXCLUDED.metadata_id,
                content_preview = EXCLUDED.content_preview,
                order_index = EXCLUDED.order_index,
                page_start = EXCLUDED.page_start,
                page_end = EXCLUDED.page_end,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            document_id,
            document_doc.get("title"),
            _storage_object_key(document_doc),
            document_doc.get("keysearch"),
            topic_id,
            metadata_id,
            _content_preview(document_doc),
            document_doc.get("order_index"),
            document_doc.get("page_start"),
            document_doc.get("page_end"),
        )
        await conn.execute(
            """
            INSERT INTO DOC_CONCEPT (concept_id, document_id)
            VALUES ($1, $2)
            ON CONFLICT (concept_id, document_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            """,
            pg_concept["concept_id"],
            row["document_id"],
        )
        await self._mongo_upsert_aux(
            "doc_concepts",
            {"concept_id": pg_concept["concept_id"], "document_id": row["document_id"]},
            {},
        )
        typedoc = await self._pg_upsert_typedoc(conn, document_doc.get("typedocs"))
        if typedoc:
            await conn.execute(
                """
                INSERT INTO DOC_TYPE (document_id, typedoc_id)
                VALUES ($1, $2)
                ON CONFLICT (document_id, typedoc_id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
                """,
                row["document_id"],
                typedoc["typedoc_id"],
            )
            await self._mongo_upsert_aux(
                "doc_types",
                {"document_id": row["document_id"], "typedoc_id": typedoc["typedoc_id"]},
                {},
            )
        # Keep DOCUMENT_KEYWORD exactly aligned with the current keysearch when
        # keyword data is present. Finalize/chunk-approve runs with keysearch empty
        # should not wipe existing approved keywords.
        if document_doc.get("keysearch") not in (None, ""):
            await conn.execute("DELETE FROM DOCUMENT_KEYWORD WHERE document_id = $1", row["document_id"])
            for keyword in _split_keywords(document_doc.get("keysearch")):
                pg_keyword = await self._pg_upsert_keyword(conn, keyword)
                await self._pg_link_document_keyword(conn, row["document_id"], pg_keyword["keyword_id"])
        return row

    # ---------- Neo4j sync helpers ----------

    async def _neo4j_sync_role_user(self, driver: AsyncDriver, pg_user: asyncpg.Record) -> None:
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            await session.run(
                """
                MERGE (r:Role {role_id: $role_id})
                SET r.name = $role_name,
                    r.description = $role_description
                MERGE (u:User {user_id: $user_id})
                SET u.name = $user_name,
                    u.birth_date = $birth_date
                MERGE (u)-[:HAS_ROLE]->(r)
                """,
                role_id=pg_user["role_id"],
                role_name=ROLE_LABELS.get(str(pg_user["role_id"]), str(pg_user["role_id"])),
                role_description="Auto-created from MongoDB users.role field",
                user_id=pg_user["user_id"],
                user_name=pg_user["name"],
                birth_date=str(pg_user["birth_date"]) if pg_user["birth_date"] else None,
            )

    async def _neo4j_sync_class(self, driver: AsyncDriver, pg_class: asyncpg.Record) -> None:
        """Create Class node and attach it to root Thing.

        Required Neo4j pattern:
        (:Thing {thing_name: 'STEM'})-[:HAS_CLASS]->(:Class)
        """
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            await session.run(
                """
                MERGE (root:Thing {thing_name: 'STEM'})
                SET root.name = 'STEM',
                    root.description = 'Root node of STEM learning knowledge graph'

                MERGE (c:Class {class_id: $class_id})
                SET c.pg_id = $class_id,
                    c.name = $name,
                    c.class_name = $name,
                    c.grade = $grade,
                    c.section = $section

                MERGE (root)-[:HAS_CLASS]->(c)
                """,
                class_id=pg_class["class_id"],
                name=pg_class["section"] or pg_class["class_id"],
                grade=pg_class["grade"],
                section=pg_class["section"],
            )

    async def _neo4j_sync_subject(self, driver: AsyncDriver, pg_subject: asyncpg.Record) -> None:
        """Create Subject node and attach it to its Class node(s).

        Required Neo4j pattern:
        (:Class)-[:HAS_SUBJECT]->(:Subject)
        """
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            class_rows = await conn.fetch(
                """
                SELECT c.*
                FROM CLASS c
                JOIN CLASS_SUBJECT cs ON cs.class_id = c.class_id
                WHERE cs.subject_id = $1
                """,
                pg_subject["subject_id"],
            )

        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            await session.run(
                """
                MERGE (s:Subject {subject_id: $subject_id})
                SET s.pg_id = $subject_id,
                    s.name = $name,
                    s.description = $description
                """,
                subject_id=pg_subject["subject_id"],
                name=pg_subject["name"],
                description=pg_subject["description"],
            )

        for pg_class in class_rows:
            await self._neo4j_sync_class(driver, pg_class)
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                await session.run(
                    """
                    MATCH (c:Class {class_id: $class_id})
                    MATCH (s:Subject {subject_id: $subject_id})
                    MERGE (c)-[:HAS_SUBJECT]->(s)
                    """,
                    class_id=pg_class["class_id"],
                    subject_id=pg_subject["subject_id"],
                )

    async def _neo4j_sync_topic(self, driver: AsyncDriver, pg_topic: asyncpg.Record) -> None:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            pg_subject = await conn.fetchrow("SELECT * FROM SUBJECT WHERE subject_id = $1", pg_topic["subject_id"])
        if pg_subject:
            await self._neo4j_sync_subject(driver, pg_subject)
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            await session.run(
                """
                MERGE (t:Topic {topic_id: $topic_id})
                SET t.pg_id = $topic_id,
                    t.name = $name
                WITH t
                MATCH (s:Subject {subject_id: $subject_id})
                MERGE (s)-[:HAS_TOPIC]->(t)
                MERGE (t)-[:BELONGS_TO_SUBJECT]->(s)
                """,
                topic_id=pg_topic["topic_id"],
                name=pg_topic["name"],
                subject_id=pg_topic["subject_id"],
            )

    async def _neo4j_sync_concept(self, driver: AsyncDriver, pg_concept: asyncpg.Record) -> None:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            pg_topic = await conn.fetchrow("SELECT * FROM TOPIC WHERE topic_id = $1", pg_concept["topic_id"])
        if pg_topic:
            await self._neo4j_sync_topic(driver, pg_topic)
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            await session.run(
                """
                MERGE (c:Concept {concept_id: $concept_id})
                SET c.pg_id = $concept_id,
                    c.title = $name,
                    c.name = $name,
                    c.definition = $definition,
                    c.file_path = $file_path
                WITH c
                MATCH (t:Topic {topic_id: $topic_id})
                MERGE (t)-[:HAS_CONCEPT]->(c)
                MERGE (c)-[:BELONGS_TO_TOPIC]->(t)
                """,
                concept_id=pg_concept["concept_id"],
                name=pg_concept["name"],
                definition=pg_concept["definition"],
                file_path=pg_concept["file_path"],
                topic_id=pg_concept["topic_id"],
            )

    async def _neo4j_sync_document(self, driver: AsyncDriver, pg_document: asyncpg.Record) -> None:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            concept_rows = await conn.fetch(
                """
                SELECT c.* FROM CONCEPT c
                JOIN DOC_CONCEPT dc ON dc.concept_id = c.concept_id
                WHERE dc.document_id = $1
                """,
                pg_document["document_id"],
            )
            keyword_rows = await conn.fetch(
                """
                SELECT k.* FROM KEYWORD k
                JOIN DOCUMENT_KEYWORD dk ON dk.keyword_id = k.keyword_id
                WHERE dk.document_id = $1
                """,
                pg_document["document_id"],
            )
        for pg_concept in concept_rows:
            await self._neo4j_sync_concept(driver, pg_concept)
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            await session.run(
                """
                MERGE (d:Document {document_id: $document_id})
                SET d.pg_id = $document_id,
                    d.title = $title,
                    d.file_path = $file_path,
                    d.keysearch = $keysearch,
                    d.metadata_id = $metadata_id,
                    d.content_preview = $content_preview,
                    d.order_index = $order_index,
                    d.page_start = $page_start,
                    d.page_end = $page_end
                """,
                document_id=pg_document["document_id"],
                title=pg_document["title"],
                file_path=pg_document["file_path"],
                keysearch=pg_document["keysearch"],
                metadata_id=pg_document["metadata_id"],
                content_preview=pg_document["content_preview"],
                order_index=pg_document["order_index"],
                page_start=pg_document["page_start"],
                page_end=pg_document["page_end"],
            )
            for pg_concept in concept_rows:
                await session.run(
                    """
                    MATCH (c:Concept {concept_id: $concept_id})
                    MATCH (d:Document {document_id: $document_id})
                    MERGE (c)-[:HAS_DOCUMENT]->(d)
                    MERGE (d)-[:COVERS_CONCEPT]->(c)
                    """,
                    concept_id=pg_concept["concept_id"],
                    document_id=pg_document["document_id"],
                )
            for keyword in keyword_rows:
                aliases = keyword["aliases"]
                if isinstance(aliases, str):
                    aliases = json.loads(aliases)
                await session.run(
                    """
                    MATCH (d:Document {document_id: $document_id})
                    MERGE (k:Keyword {keyword_id: $keyword_id})
                    SET k.pg_id = $keyword_id,
                        k.keyword_name = $keyword_name,
                        k.name = $keyword_name,
                        k.normalized_name = $normalized_name,
                        k.aliases = $aliases
                    MERGE (d)-[:HAS_KEYWORD]->(k)
                    """,
                    document_id=pg_document["document_id"],
                    keyword_id=keyword["keyword_id"],
                    keyword_name=keyword["keyword_name"],
                    normalized_name=keyword["normalized_name"],
                    aliases=aliases or [],
                )

    # ---------- Public sync methods ----------

    async def sync_class(self, map_id: str) -> dict[str, Any]:
        await self.ensure_targets_ready()
        doc = await self.classes.find_by_map_id(map_id)
        if not doc:
            raise ValueError("Class not found in MongoDB")
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            pg_row = await self._pg_upsert_class(conn, doc)
        driver = get_neo4j_driver()
        await self._neo4j_sync_class(driver, pg_row)
        return {"entity": "class", "map_id": map_id, "pg_id": pg_row["class_id"]}

    async def sync_subject(self, map_id: str) -> dict[str, Any]:
        await self.ensure_targets_ready()
        doc = await self.subjects.find_by_map_id(map_id)
        if not doc:
            raise ValueError("Subject not found in MongoDB")
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            pg_row = await self._pg_upsert_subject(conn, doc)
        driver = get_neo4j_driver()
        await self._neo4j_sync_subject(driver, pg_row)
        return {"entity": "subject", "map_id": map_id, "pg_id": pg_row["subject_id"]}

    async def sync_topic(self, map_id: str) -> dict[str, Any]:
        await self.ensure_targets_ready()
        doc = await self.topics.find_by_map_id(map_id)
        if not doc:
            raise ValueError("Topic not found in MongoDB")
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            pg_row = await self._pg_upsert_topic(conn, doc)
        driver = get_neo4j_driver()
        await self._neo4j_sync_topic(driver, pg_row)
        return {"entity": "topic", "map_id": map_id, "pg_id": pg_row["topic_id"]}

    async def sync_concept(self, map_id: str) -> dict[str, Any]:
        await self.ensure_targets_ready()
        doc = await self.concepts.find_by_map_id(map_id)
        if not doc:
            raise ValueError("Concept not found in MongoDB")
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            pg_row = await self._pg_upsert_concept(conn, doc)
        driver = get_neo4j_driver()
        await self._neo4j_sync_concept(driver, pg_row)
        return {"entity": "concept", "map_id": map_id, "pg_id": pg_row["concept_id"]}

    async def sync_user(self, map_id: str) -> dict[str, Any]:
        await self.ensure_targets_ready()
        doc = await self.users.find_by_map_id(map_id)
        if not doc:
            raise ValueError("User not found in MongoDB")
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            pg_row = await self._pg_upsert_user(conn, doc)
        driver = get_neo4j_driver()
        await self._neo4j_sync_role_user(driver, pg_row)
        return {"entity": "user", "map_id": map_id, "pg_id": pg_row["user_id"]}

    async def sync_document(self, map_id: str) -> dict[str, Any]:
        await self.ensure_targets_ready()
        doc = await self.documents.find_by_map_id(map_id)
        if not doc:
            raise ValueError("Document not found in MongoDB")
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            pg_row = await self._pg_upsert_document(conn, doc)
        driver = get_neo4j_driver()
        await self._neo4j_sync_document(driver, pg_row)
        return {"entity": "document", "map_id": map_id, "pg_id": pg_row["document_id"]}

    async def sync_all(self) -> dict[str, Any]:
        await self.ensure_targets_ready()
        summary: dict[str, list[dict[str, Any]]] = {
            "classes": [],
            "users": [],
            "subjects": [],
            "topics": [],
            "concepts": [],
            "documents": [],
        }
        for doc in await self.classes.find_many(limit=10000):
            summary["classes"].append(await self.sync_class(doc["map_id"]))
        for doc in await self.users.find_many(limit=10000):
            summary["users"].append(await self.sync_user(doc["map_id"]))
        for doc in await self.subjects.find_many(limit=10000):
            summary["subjects"].append(await self.sync_subject(doc["map_id"]))
        for doc in await self.topics.find_many(limit=10000):
            summary["topics"].append(await self.sync_topic(doc["map_id"]))
        for doc in await self.concepts.find_many(limit=10000):
            summary["concepts"].append(await self.sync_concept(doc["map_id"]))
        for doc in await self.documents.find_many(limit=10000):
            summary["documents"].append(await self.sync_document(doc["map_id"]))
        return {"ok": True, "summary": summary}

    async def sync_entity(self, entity: str, map_id: str) -> dict[str, Any]:
        if entity == "classes":
            return await self.sync_class(map_id)
        if entity == "users":
            return await self.sync_user(map_id)
        if entity == "subjects":
            return await self.sync_subject(map_id)
        if entity == "topics":
            return await self.sync_topic(map_id)
        if entity == "concepts":
            return await self.sync_concept(map_id)
        if entity == "documents":
            return await self.sync_document(map_id)
        raise ValueError("entity must be one of: classes, users, subjects, topics, concepts, documents")


async def safe_auto_sync(entity: str, map_id: str) -> dict[str, Any] | None:
    """Best-effort sync after create/upload.

    It should not break MongoDB/Google Drive upload if PostgreSQL or Neo4j is temporarily offline.
    The user can call POST /api/sync/all later to backfill.
    """
    if not settings.AUTO_SYNC_ENABLED:
        return None
    try:
        return await SyncService().sync_entity(entity, map_id)
    except Exception as exc:
        return {"ok": False, "entity": entity, "map_id": map_id, "error": str(exc)}
