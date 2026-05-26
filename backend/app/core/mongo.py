from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import CollectionInvalid, OperationFailure

from app.core.config import settings

_client: AsyncIOMotorClient | None = None

# Collections aligned with the provided Mongo migration file.
# MongoDB creates the database automatically when collections/indexes are created.
MONGO_COLLECTIONS: tuple[str, ...] = (
    "roles",
    "users",
    "subjects",
    "classes",
    "typedocs",
    "topics",
    "concepts",
    "documents",
    "class_subjects",
    "doc_concepts",
    "doc_types",
    "logs",
    "document_metadata",
    "keywords",
    "document_keywords",
    "topic_bags",
)


def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URI)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    return get_mongo_client()[settings.MONGO_DB]


async def close_mongo_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def ensure_collections() -> None:
    """Create MongoDB collections on application startup.

    MongoDB has no explicit CREATE DATABASE command; creating collections or
    indexes materializes the database so Compass can see it before the first upload.
    """
    db = get_database()
    existing = set(await db.list_collection_names())

    for collection_name in MONGO_COLLECTIONS:
        if collection_name in existing:
            continue
        try:
            await db.create_collection(collection_name)
        except CollectionInvalid:
            pass


async def _safe_create_index(collection, keys, **kwargs) -> None:
    try:
        await collection.create_index(keys, **kwargs)
    except OperationFailure as exc:
        # During development, old data can violate a newly added unique index.
        # The app should still boot; the duplicate issue can be cleaned manually.
        if "duplicate" not in str(exc).lower():
            raise


async def create_indexes() -> None:
    """Create indexes for both the new *_id fields and legacy map_id fields.

    The current API still accepts map_id/classMapId/...; the new DB target uses
    subject_id/topic_id/... when syncing. Sparse unique indexes let existing
    map_id-only documents coexist until code backfills the new names.
    """
    db = get_database()

    await _safe_create_index(db.roles, "role_id", unique=True, sparse=True)
    await _safe_create_index(db.users, "user_id", unique=True, sparse=True)
    await _safe_create_index(db.users, "map_id", unique=True, sparse=True)
    await _safe_create_index(db.users, "email", unique=True, sparse=True)

    await _safe_create_index(db.subjects, "subject_id", unique=True, sparse=True)
    await _safe_create_index(db.subjects, "map_id", unique=True, sparse=True)
    await _safe_create_index(db.subjects, "classMapId")
    await _safe_create_index(db.subjects, "class_id", sparse=True)
    await _safe_create_index(db.subjects, [("classMapId", 1), ("name", 1)], unique=True, sparse=True)

    await _safe_create_index(db.classes, "class_id", unique=True, sparse=True)
    await _safe_create_index(db.classes, "map_id", unique=True, sparse=True)

    await _safe_create_index(db.typedocs, "typedoc_id", unique=True, sparse=True)

    await _safe_create_index(db.topics, "topic_id", unique=True, sparse=True)
    await _safe_create_index(db.topics, "map_id", unique=True, sparse=True)
    await _safe_create_index(db.topics, "subjectMapId")
    await _safe_create_index(db.topics, "subject_id", sparse=True)
    await _safe_create_index(db.topics, [("subjectMapId", 1), ("name", 1)], unique=True, sparse=True)

    await _safe_create_index(db.concepts, "concept_id", unique=True, sparse=True)
    await _safe_create_index(db.concepts, "map_id", unique=True, sparse=True)
    await _safe_create_index(db.concepts, "topicMapId")
    await _safe_create_index(db.concepts, "topic_id", sparse=True)
    await _safe_create_index(db.concepts, [("topicMapId", 1), ("name", 1)], unique=True, sparse=True)

    await _safe_create_index(db.documents, "document_id", unique=True, sparse=True)
    await _safe_create_index(db.documents, "map_id", unique=True, sparse=True)
    await _safe_create_index(db.documents, "conceptMapId")
    await _safe_create_index(db.documents, "topic_id", sparse=True)
    await _safe_create_index(db.documents, "typedocs")
    await _safe_create_index(db.documents, "status")
    await _safe_create_index(db.documents, "storage.objectKey")

    await _safe_create_index(db.document_metadata, "document_id", unique=True, sparse=True)
    await _safe_create_index(db.keywords, "keyword_id", unique=True, sparse=True)
    await _safe_create_index(db.keywords, "normalized_name", sparse=True)
    await _safe_create_index(db.document_keywords, [("document_id", 1), ("keyword_id", 1)], unique=True, sparse=True)
    await _safe_create_index(db.topic_bags, "topic_bag_id", unique=True, sparse=True)
    await _safe_create_index(db.topic_bags, "topic_id", unique=True, sparse=True)


async def ensure_database_ready() -> None:
    """Ensure MongoDB database, collections and indexes exist at startup."""
    await ensure_collections()
    await create_indexes()
