from fastapi import APIRouter

from app.api.routes import (
    classes,
    concepts,
    documents,
    extract_chunks,
    extract_debug,
    extract_jobs,
    extract_keywords,
    extract_lessons,
    extract_topics,
    files,
    health,
    keyword_search,
    seed,
    subjects,
    sync,
    topics,
    users,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(seed.router, prefix="/seed", tags=["Seed"])
api_router.include_router(sync.router, prefix="/sync", tags=["Sync"])
api_router.include_router(classes.router, prefix="/classes", tags=["Classes"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["Subjects"])
api_router.include_router(topics.router, prefix="/topics", tags=["Topics"])
api_router.include_router(concepts.router, prefix="/concepts", tags=["Concepts"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(files.router, prefix="/files", tags=["Files"])

# AI-Extract pipeline APIs are copied unchanged in behavior; route prefixes are already absolute.
api_router.include_router(extract_jobs.router)
api_router.include_router(extract_topics.router)
api_router.include_router(extract_lessons.router)
api_router.include_router(extract_chunks.router)
api_router.include_router(extract_keywords.router)
api_router.include_router(extract_debug.router)

# Keyword search API built from Neo4j TopicBag/Keyword/Document graph.
api_router.include_router(keyword_search.router)
