from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.repositories.learning_repository import DocumentRepository
from app.schemas.file_schema import DocumentUploadResponse
from app.schemas.learning_schema import DocumentResponse
from app.services.file_service import FileService

router = APIRouter()
file_service = FileService()
repo = DocumentRepository()


@router.post("", response_model=DocumentUploadResponse)
async def create_document_with_file(
    file: UploadFile = File(..., description="File gốc của Document"),
    map_id: str = Form(..., description="Ví dụ: HH11_T1_C1_D1"),
    title: str = Form(..., description="Tên học liệu/document"),
    conceptMapId: str = Form(..., description="map_id của Concept, ví dụ: HH11_T1_C1"),
    typedocs: str = Form(..., description="1=document, 2=image, 3=video. Đây là field, không phải collection."),
    description: str | None = Form(default=None),
    keysearch: str | None = Form(default=None),
):
    """
    Tạo Document bằng Form và upload file ngay trong cùng API.

    Swagger sẽ hiện từng ô nhập + nút chọn file. Các field hệ thống như createdBy, updatedBy, sourceName, sourceUrl, language, licenseNote sẽ do backend tự gán/default.
    Backend tự:
    1. Resolve conceptMapId -> topic -> subject -> class.
    2. Tạo objectKey/logical path theo STEM/{classSlug}/documents/{documentSlug}/{fileName}.
    3. Upload file lên Google Drive.
    4. Lưu metadata vào MongoDB collection documents.
    """
    try:
        return await file_service.upload_document(
            file=file,
            map_id=map_id,
            title=title,
            conceptMapId=conceptMapId,
            typedocs=typedocs,
            description=description,
            keysearch=keysearch,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    conceptMapId: str | None = None,
    typedocs: str | None = None,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    query = {}
    if conceptMapId:
        query["conceptMapId"] = conceptMapId
    if typedocs:
        query["typedocs"] = typedocs
    if status:
        query["status"] = status
    return await repo.find_many(query=query, limit=limit)


@router.get("/{map_id}", response_model=DocumentResponse)
async def get_document(map_id: str):
    doc = await repo.find_by_map_id(map_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
