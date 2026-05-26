from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.models.enums import EntityType
from app.repositories.learning_repository import ConceptRepository
from app.schemas.learning_schema import ConceptResponse
from app.services.file_service import FileService
from app.services.learning_service import LearningService

router = APIRouter()
service = LearningService()
file_service = FileService()
repo = ConceptRepository()


@router.post("", response_model=ConceptResponse)
async def create_concept(
    map_id: str = Form(..., description="Ví dụ: TH10_T1_C1"),
    topicMapId: str = Form(..., description="map_id của Topic, ví dụ: TH10_T1"),
    name: str = Form(..., description="Tên concept/kiến thức nền"),
    definition: str | None = Form(default=None),
    conceptNumber: int | None = Form(default=None),
    filePath: str | None = Form(default="", description="Có thể bỏ trống nếu upload file"),
    file: UploadFile | None = File(default=None, description="File gốc cấp Concept, nếu có"),
):
    """Tạo Concept bằng Form. Nếu gửi file, hệ thống upload lên Google Drive và tự cập nhật filePath."""
    try:
        await service.create_concept(
            {
                "map_id": map_id,
                "topicMapId": topicMapId,
                "name": name,
                "filePath": filePath or "",
                "definition": definition,
                "conceptNumber": conceptNumber,
            }
        )
        if file is not None and file.filename:
            await file_service.upload_entity_file(file=file, entity_type=EntityType.concepts, map_id=map_id)
        created = await repo.find_by_map_id(map_id)
        return created
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=list[ConceptResponse])
async def list_concepts(topicMapId: str | None = None, limit: int = Query(default=100, ge=1, le=500)):
    query = {"topicMapId": topicMapId} if topicMapId else {}
    return await repo.find_many(query=query, limit=limit)


@router.get("/{map_id}", response_model=ConceptResponse)
async def get_concept(map_id: str):
    doc = await repo.find_by_map_id(map_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Concept not found")
    return doc
