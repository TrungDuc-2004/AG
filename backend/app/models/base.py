from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MongoBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


def mongo_dump(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="python", exclude_none=True)
