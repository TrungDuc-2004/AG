from fastapi import APIRouter

from app.services.seed_service import SeedService

router = APIRouter()
service = SeedService()


@router.post("/mongo-sample")
async def seed_mongo_sample():
    return await service.seed_mongo_sample()
