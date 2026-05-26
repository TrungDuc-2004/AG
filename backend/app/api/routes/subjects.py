from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.models.enums import EntityType
from app.repositories.learning_repository import SubjectRepository
from app.schemas.learning_schema import SubjectResponse
from app.services.file_service import FileService
from app.services.learning_service import LearningService

router = APIRouter()
service = LearningService()
file_service = FileService()
repo = SubjectRepository()


@router.post("", response_model=SubjectResponse)
async def create_subject(
    map_id: str = Form(..., description="Ví dụ: TH10"),
    name: str = Form(..., description="Ví dụ: Tin học"),
    classMapId: str = Form(..., description="map_id của Class, ví dụ: 10"),
    description: str | None = Form(default=None),
    filePath: str | None = Form(default="", description="Có thể bỏ trống nếu upload file"),
    file: UploadFile | None = File(default=None, description="File gốc cấp Subject, nếu có"),
):
    """Tạo Subject bằng Form. Nếu gửi file, hệ thống upload lên Google Drive và tự cập nhật filePath."""
    try:
        await service.create_subject(
            {
                "map_id": map_id,
                "name": name,
                "filePath": filePath or "",
                "classMapId": classMapId,
                "description": description,
            }
        )
        if file is not None and file.filename:
            await file_service.upload_entity_file(file=file, entity_type=EntityType.subjects, map_id=map_id)
        created = await repo.find_by_map_id(map_id)
        return created
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=list[SubjectResponse])
async def list_subjects(classMapId: str | None = None, limit: int = Query(default=100, ge=1, le=500)):
    query = {"classMapId": classMapId} if classMapId else {}
    return await repo.find_many(query=query, limit=limit)


@router.get("/{map_id}", response_model=SubjectResponse)
async def get_subject(map_id: str):
    doc = await repo.find_by_map_id(map_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Subject not found")
    return doc
