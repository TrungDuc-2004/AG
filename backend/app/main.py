from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.mongo import close_mongo_client, ensure_database_ready
from app.core.neo4j import close_neo4j_driver
from app.core.postgres import close_pg_pool
from app.services.sync_service import SyncService


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_database_ready()

    # Best-effort init for PostgreSQL/Neo4j. If they are not running yet, backend still starts;
    # upload/create APIs will try again during auto-sync, and /api/sync/init-targets can be called later.
    app.state.sync_startup_warning = None
    try:
        await SyncService().ensure_targets_ready()
    except Exception as exc:  # pragma: no cover - startup warning only
        app.state.sync_startup_warning = str(exc)

    yield
    await close_mongo_client()
    await close_pg_pool()
    await close_neo4j_driver()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root() -> dict:
    return {
        "message": "STEM FastAPI backend is running",
        "docs": "/docs",
        "syncStartupWarning": getattr(app.state, "sync_startup_warning", None),
    }
