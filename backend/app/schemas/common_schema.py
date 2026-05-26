from typing import Any

from pydantic import BaseModel


class SyncMixin(BaseModel):
    sync: dict[str, Any] | None = None
