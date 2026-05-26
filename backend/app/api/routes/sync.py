from fastapi import APIRouter, HTTPException

from app.services.sync_service import SyncService

router = APIRouter()
service = SyncService()


@router.get("/health")
async def sync_health():
    """Kiểm tra kết nối PostgreSQL và Neo4j, đồng thời tự tạo DB/schema/constraints nếu có thể."""
    return await service.health()


@router.get("/check-mongo")
async def check_mongo_for_sync():
    """Kiểm tra MongoDB hiện có đủ dữ liệu/quan hệ để sync sang PostgreSQL và Neo4j không."""
    return await service.check_mongo_compatibility()


@router.post("/init-targets")
async def init_sync_targets():
    """Tự tạo PostgreSQL database/schema và Neo4j constraints/root node."""
    try:
        await service.ensure_targets_ready()
        return {"ok": True, "message": "PostgreSQL and Neo4j targets are ready"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/all")
async def sync_all():
    """Backfill toàn bộ dữ liệu hiện có trong MongoDB sang PostgreSQL và Neo4j."""
    try:
        return await service.sync_all()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{entity}/{map_id}")
async def sync_one(entity: str, map_id: str):
    """Sync một entity cụ thể: classes/users/subjects/topics/concepts/documents."""
    try:
        return await service.sync_entity(entity, map_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
