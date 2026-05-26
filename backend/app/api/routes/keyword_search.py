from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.schemas.search_keyword import KeywordSearchRequest, KeywordSearchResponse
from app.services.search.keyword_extractor import KeywordExtractor
from app.services.search.keyword_search_service import KeywordSearchService
from app.services.search.e5_embedding_service import E5EmbeddingService
from app.services.search.neo4j_keyword_search_service import Neo4jKeywordSearchService
from app.core.config import settings


router = APIRouter(tags=["Keyword Search"])


def build_service() -> KeywordSearchService:
    neo = Neo4jKeywordSearchService(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )
    return KeywordSearchService(
        neo4j_search_service=neo,
        embedding_service=E5EmbeddingService(),
        keyword_extractor=KeywordExtractor(),
    )


@router.post("/search/keyword", response_model=KeywordSearchResponse)
def search_keyword(payload: KeywordSearchRequest):
    service = build_service()
    try:
        return service.search(query=payload.query, limit=payload.limit)
    finally:
        service.neo4j_search_service.close()


@router.get("/search-ui", response_class=HTMLResponse)
def search_ui():
    with open("app/static/search_test.html", "r", encoding="utf-8") as f:
        return f.read()
