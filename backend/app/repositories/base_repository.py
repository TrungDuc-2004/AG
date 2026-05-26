from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.core.mongo import get_database


def serialize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


class MongoRepository:
    collection_name: str

    def __init__(self, collection_name: str) -> None:
        self.collection_name = collection_name

    @property
    def collection(self):
        return get_database()[self.collection_name]

    async def insert_one(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            result = await self.collection.insert_one(data)
        except DuplicateKeyError as exc:
            raise ValueError(f"Duplicate record in collection '{self.collection_name}'") from exc
        doc = await self.collection.find_one({"_id": result.inserted_id})
        return serialize_doc(doc)  # type: ignore[return-value]

    async def upsert_by_map_id(self, map_id: str, data: dict[str, Any]) -> dict[str, Any]:
        data = dict(data)
        data["updatedAt"] = datetime.now(timezone.utc)
        if "createdAt" not in data:
            data["createdAt"] = datetime.now(timezone.utc)
        await self.collection.update_one({"map_id": map_id}, {"$set": data}, upsert=True)
        doc = await self.collection.find_one({"map_id": map_id})
        return serialize_doc(doc)  # type: ignore[return-value]

    async def find_by_map_id(self, map_id: str) -> dict[str, Any] | None:
        return serialize_doc(await self.collection.find_one({"map_id": map_id}))

    async def find_by_id(self, doc_id: str) -> dict[str, Any] | None:
        try:
            oid = ObjectId(doc_id)
        except Exception:
            return None
        return serialize_doc(await self.collection.find_one({"_id": oid}))

    async def find_many(self, query: dict[str, Any] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        cursor = self.collection.find(query or {}).limit(limit)
        return [serialize_doc(doc) async for doc in cursor]  # type: ignore[misc]

    async def update_by_map_id(self, map_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        data = dict(data)
        data["updatedAt"] = datetime.now(timezone.utc)
        result = await self.collection.update_one({"map_id": map_id}, {"$set": data})
        if result.matched_count == 0:
            return None
        return await self.find_by_map_id(map_id)
