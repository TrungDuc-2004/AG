from fastapi import APIRouter, Form, HTTPException, Query

from app.repositories.learning_repository import ClassRepository
from app.schemas.learning_schema import ClassResponse
from app.services.learning_service import LearningService

router = APIRouter()
service = LearningService()
repo = ClassRepository()


@router.post("", response_model=ClassResponse)
async def create_class(
    map_id: str = Form(..., description="Ví dụ: 10, 11, 12"),
    name: str = Form(..., description="Ví dụ: Lớp 10"),
):
    """Tạo Class bằng các ô nhập Form, không cần nhập JSON."""
    try:
        return await service.create_class({"map_id": map_id, "name": name})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=list[ClassResponse])
async def list_classes(limit: int = Query(default=100, ge=1, le=500)):
    return await repo.find_many(limit=limit)


@router.get("/{map_id}", response_model=ClassResponse)
async def get_class(map_id: str):
    doc = await repo.find_by_map_id(map_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Class not found")
    return doc
