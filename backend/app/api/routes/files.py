from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from urllib.parse import quote

from app.models.enums import EntityType
from app.schemas.file_schema import DocumentUploadResponse, EntityFileUploadResponse, PresignedUrlResponse
from app.services.file_service import FileService

router = APIRouter()
service = FileService()


@router.post("/upload-entity", response_model=EntityFileUploadResponse)
async def upload_entity_file(
    file: UploadFile = File(...),
    entity_type: EntityType = Form(..., description="subjects | topics | concepts"),
    map_id: str = Form(...),
):
    try:
        return await service.upload_entity_file(file=file, entity_type=entity_type, map_id=map_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/upload-document", response_model=DocumentUploadResponse)
async def upload_document_file(
    file: UploadFile = File(...),
    map_id: str = Form(...),
    title: str = Form(...),
    conceptMapId: str = Form(...),
    typedocs: str = Form(..., description="1=document, 2=image, 3=video"),
    description: str | None = Form(default=None),
    keysearch: str | None = Form(default=None),
    createdBy: str = Form(default="USER_001"),
    updatedBy: str = Form(default="USER_001"),
    sourceName: str | None = Form(default=None),
    sourceUrl: str | None = Form(default=None),
    language: str = Form(default="vi"),
    licenseNote: str | None = Form(default=None),
):
    try:
        return await service.upload_document(
            file=file,
            map_id=map_id,
            title=title,
            conceptMapId=conceptMapId,
            typedocs=typedocs,
            description=description,
            keysearch=keysearch,
            createdBy=createdBy,
            updatedBy=updatedBy,
            sourceName=sourceName,
            sourceUrl=sourceUrl,
            language=language,
            licenseNote=licenseNote,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/documents/{map_id}/download")
async def download_document_file(map_id: str):
    data = await service.get_document_download(map_id)
    if not data:
        raise HTTPException(status_code=404, detail="Document not found")

    filename = data["filename"]
    quoted_filename = quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}",
    }
    return StreamingResponse(
        data["stream"],
        media_type=data["mimeType"],
        headers=headers,
    )


@router.get("/documents/{map_id}/presigned-url", response_model=PresignedUrlResponse)
async def get_document_presigned_url(
    map_id: str,
    expires_seconds: int = Query(default=3600, ge=60, le=86400),
):
    data = await service.get_presigned_document_url(map_id, expires_seconds)
    if not data:
        raise HTTPException(status_code=404, detail="Document not found")
    return data
