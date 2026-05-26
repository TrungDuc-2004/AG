from datetime import date

from fastapi import APIRouter, Form, HTTPException, Query

from app.repositories.learning_repository import UserRepository
from app.schemas.learning_schema import UserResponse
from app.services.learning_service import LearningService

router = APIRouter()
service = LearningService()
repo = UserRepository()


@router.post("", response_model=UserResponse)
async def create_user(
    map_id: str = Form(..., description="Ví dụ: USER_001"),
    name: str = Form(...),
    email: str = Form(...),
    role: str = Form(default="user", description="Chỉ là field trong users, không tạo collection roles"),
    gender: str | None = Form(default=None),
    address: str | None = Form(default=None),
    birthDate: date | None = Form(default=None),
    avatarImage: str | None = Form(default=None),
):
    """Tạo User bằng các ô nhập Form, không cần nhập JSON."""
    try:
        return await service.create_user(
            {
                "map_id": map_id,
                "name": name,
                "email": email,
                "gender": gender,
                "address": address,
                "birthDate": birthDate,
                "role": role,
                "avatarImage": avatarImage,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=list[UserResponse])
async def list_users(limit: int = Query(default=100, ge=1, le=500)):
    return await repo.find_many(limit=limit)


@router.get("/{map_id}", response_model=UserResponse)
async def get_user(map_id: str):
    doc = await repo.find_by_map_id(map_id)
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return doc
