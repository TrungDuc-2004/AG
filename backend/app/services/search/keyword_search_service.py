from typing import Any

from app.schemas.search_keyword import (
    KeywordSearchGroups,
    KeywordSearchResponse,
    KeywordSearchResult,
    LevelSearchResult,
    MatchedKeyword,
    PathNode,
)
from app.services.search.e5_embedding_service import E5EmbeddingService
from app.services.search.keyword_extractor import KeywordExtractor
from app.services.search.neo4j_keyword_search_service import Neo4jKeywordSearchService


class KeywordSearchService:
    def __init__(
        self,
        neo4j_search_service: Neo4jKeywordSearchService,
        embedding_service: E5EmbeddingService,
        keyword_extractor: KeywordExtractor,
    ):
        self.neo4j_search_service = neo4j_search_service
        self.embedding_service = embedding_service
        self.keyword_extractor = keyword_extractor

    def search(self, query: str, limit: int = 5) -> KeywordSearchResponse:
        extracted_keywords = self.keyword_extractor.extract(query)
        if not extracted_keywords:
            extracted_keywords = [query]

        merged_docs: dict[str, dict[str, Any]] = {}

        for query_keyword in extracted_keywords:
            docs = self.neo4j_search_service.search_keyword_documents(
                query_keyword=query_keyword,
                limit=limit,
            )

            for doc in docs:
                doc_id = doc.get("document_id")
                if doc_id is None:
                    continue

                doc["matched_keywords"] = [
                    MatchedKeyword(
                        keyword_id=doc.get("matched_keyword_id"),
                        keyword_name=doc.get("matched_keyword_name") or query_keyword,
                        aliases=[],
                    )
                ]

                old = merged_docs.get(doc_id)
                if old is None or float(doc.get("score", 0)) > float(old.get("score", 0)):
                    merged_docs[doc_id] = doc

        sorted_rows = sorted(
            merged_docs.values(),
            key=lambda x: float(x.get("score", 0)),
            reverse=True,
        )[:limit]

        results = [self._format_document_result(row) for row in sorted_rows]
        groups = self._build_groups(sorted_rows)

        return KeywordSearchResponse(
            query=query,
            extracted_keywords=extracted_keywords,
            results=results,
            groups=groups,
        )

    def _path_nodes(self, row: dict[str, Any]) -> tuple[PathNode, PathNode, PathNode, PathNode]:
        subject = PathNode(id=row.get("subject_id"), name=row.get("subject_name"))
        topic = PathNode(id=row.get("topic_id"), name=row.get("topic_name"))
        concept = PathNode(
            id=row.get("concept_id"),
            title=row.get("concept_title") or row.get("concept_name"),
            file_path=row.get("concept_file_path"),
        )
        document = PathNode(
            id=row.get("document_id"),
            title=row.get("document_title"),
            file_path=row.get("document_file_path"),
        )
        return subject, topic, concept, document

    def _format_document_result(self, row: dict[str, Any]) -> KeywordSearchResult:
        subject, topic, concept, document = self._path_nodes(row)

        document_keywords = [kw for kw in (row.get("document_keywords") or []) if kw]
        matched_keywords = row.get("matched_keywords") or []

        return KeywordSearchResult(
            score=float(row.get("score", 0)),
            result_type="document",
            match_type=row.get("match_type") or "exact_keyword",
            subject=subject,
            topic=topic,
            concept=concept,
            document=document,
            matched_keywords=matched_keywords,
            document_keywords=document_keywords,
            content_preview=row.get("document_content_preview"),
            file_path=row.get("document_file_path"),
            page_start=row.get("document_page_start"),
            page_end=row.get("document_page_end"),
            raw={k: v for k, v in row.items() if k not in {"matched_keywords"}},
        )

    def _build_groups(self, rows: list[dict[str, Any]]) -> KeywordSearchGroups:
        subject_map: dict[str, LevelSearchResult] = {}
        topic_map: dict[str, LevelSearchResult] = {}
        concept_map: dict[str, LevelSearchResult] = {}
        document_map: dict[str, LevelSearchResult] = {}

        for row in rows:
            score = float(row.get("score", 0))
            subject, topic, concept, document = self._path_nodes(row)
            matched_names = [m.keyword_name for m in (row.get("matched_keywords") or [])]

            self._upsert_group(subject_map, subject.id, LevelSearchResult(
                result_type="subject",
                id=subject.id,
                name=subject.name,
                score=score,
                matched_document_count=1,
                matched_keywords=matched_names,
                subject=subject,
            ), score, matched_names)

            self._upsert_group(topic_map, topic.id, LevelSearchResult(
                result_type="topic",
                id=topic.id,
                name=topic.name,
                score=score,
                matched_document_count=1,
                matched_keywords=matched_names,
                subject=subject,
                topic=topic,
            ), score, matched_names)

            self._upsert_group(concept_map, concept.id, LevelSearchResult(
                result_type="concept",
                id=concept.id,
                title=concept.title,
                file_path=concept.file_path,
                score=score,
                matched_document_count=1,
                matched_keywords=matched_names,
                subject=subject,
                topic=topic,
                concept=concept,
            ), score, matched_names)

            self._upsert_group(document_map, document.id, LevelSearchResult(
                result_type="document",
                id=document.id,
                title=document.title,
                file_path=document.file_path,
                score=score,
                matched_document_count=1,
                matched_keywords=matched_names,
                subject=subject,
                topic=topic,
                concept=concept,
                document=document,
            ), score, matched_names)

        return KeywordSearchGroups(
            subjects=sorted(subject_map.values(), key=lambda x: x.score, reverse=True),
            topics=sorted(topic_map.values(), key=lambda x: x.score, reverse=True),
            concepts=sorted(concept_map.values(), key=lambda x: x.score, reverse=True),
            documents=sorted(document_map.values(), key=lambda x: x.score, reverse=True),
        )

    @staticmethod
    def _upsert_group(
        store: dict[str, LevelSearchResult],
        key: str | None,
        item: LevelSearchResult,
        score: float,
        matched_names: list[str],
    ) -> None:
        if key is None:
            return

        old = store.get(key)
        if old is None:
            item.matched_keywords = list(dict.fromkeys(item.matched_keywords))
            store[key] = item
            return

        old.score = max(old.score, score)
        old.matched_document_count += 1
        old.matched_keywords = list(dict.fromkeys(old.matched_keywords + matched_names))
