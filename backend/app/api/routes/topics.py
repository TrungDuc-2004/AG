from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.models.enums import EntityType
from app.repositories.learning_repository import TopicRepository
from app.schemas.learning_schema import TopicResponse
from app.services.file_service import FileService
from app.services.learning_service import LearningService

router = APIRouter()
service = LearningService()
file_service = FileService()
repo = TopicRepository()


@router.post("", response_model=TopicResponse)
async def create_topic(
    map_id: str = Form(..., description="Ví dụ: TH10_T1"),
    subjectMapId: str = Form(..., description="map_id của Subject, ví dụ: TH10"),
    name: str = Form(..., description="Tên topic/chủ đề STEM"),
    description: str | None = Form(default=None),
    topicNumber: int | None = Form(default=None),
    periodCount: int | None = Form(default=None),
    filePath: str | None = Form(default="", description="Có thể bỏ trống nếu upload file"),
    file: UploadFile | None = File(default=None, description="File gốc cấp Topic, nếu có"),
):
    """Tạo Topic bằng Form. Nếu gửi file, hệ thống upload lên Google Drive và tự cập nhật filePath."""
    try:
        await service.create_topic(
            {
                "map_id": map_id,
                "subjectMapId": subjectMapId,
                "name": name,
                "description": description,
                "topicNumber": topicNumber,
                "periodCount": periodCount,
                "filePath": filePath or "",
            }
        )
        if file is not None and file.filename:
            await file_service.upload_entity_file(file=file, entity_type=EntityType.topics, map_id=map_id)
        created = await repo.find_by_map_id(map_id)
        return created
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=list[TopicResponse])
async def list_topics(subjectMapId: str | None = None, limit: int = Query(default=100, ge=1, le=500)):
    query = {"subjectMapId": subjectMapId} if subjectMapId else {}
    return await repo.find_many(query=query, limit=limit)


@router.get("/{map_id}", response_model=TopicResponse)
async def get_topic(map_id: str):
    doc = await repo.find_by_map_id(map_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Topic not found")
    return doc
