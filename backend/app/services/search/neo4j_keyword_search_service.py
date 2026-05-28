import re
import unicodedata
from typing import Any

from neo4j import GraphDatabase


def _normalize_for_compare(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _slugify(value: str | None) -> str:
    normalized = _normalize_for_compare(value)
    return normalized.replace(" ", "-")


class Neo4jKeywordSearchService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def search_keyword_documents(self, query_keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search directly on Keyword -> Document graph.

        TopicBag has been removed from PostgreSQL/Neo4j, so keyword search now uses
        the real Keyword nodes attached to Document nodes. This keeps the graph light:
        Subject -> Topic -> Concept -> Document -> Keyword.
        """
        normalized_query = _normalize_for_compare(query_keyword)
        slug_query = _slugify(query_keyword)
        raw_query = str(query_keyword or "").strip().lower()

        cypher = """
        MATCH (subject:Subject)-[:HAS_TOPIC]->(topic:Topic)
        MATCH (topic)-[:HAS_CONCEPT]->(concept:Concept)
        MATCH (concept)-[:HAS_DOCUMENT]->(document:Document)
        MATCH (document)-[:HAS_KEYWORD]->(keyword:Keyword)

        WITH subject, topic, concept, document, keyword,
             toLower(coalesce(keyword.keyword_name, keyword.name, '')) AS kw_name_lc,
             toLower(coalesce(keyword.normalized_name, '')) AS kw_norm_lc,
             coalesce(keyword.aliases, []) AS kw_aliases
        WHERE
             kw_name_lc CONTAINS $raw_query
             OR kw_norm_lc CONTAINS $normalized_query
             OR kw_norm_lc CONTAINS $slug_query
             OR any(alias IN kw_aliases WHERE toLower(toString(alias)) CONTAINS $raw_query)

        OPTIONAL MATCH (document)-[:HAS_KEYWORD]->(doc_kw:Keyword)

        WITH
            subject,
            topic,
            concept,
            document,
            keyword,
            kw_name_lc,
            kw_norm_lc,
            collect(DISTINCT doc_kw.keyword_name) AS document_keywords,
            collect(DISTINCT doc_kw.aliases) AS document_keyword_alias_groups

        RETURN
            CASE
                WHEN kw_name_lc = $raw_query THEN 1.0
                WHEN kw_norm_lc = $normalized_query OR kw_norm_lc = $slug_query THEN 0.95
                ELSE 0.75
            END AS score,
            'direct_keyword' AS match_type,
            $query_keyword AS matched_query_keyword,
            keyword.keyword_name AS matched_keyword_name,
            keyword.keyword_id AS matched_keyword_id,
            document_keywords,
            document_keyword_alias_groups,

            subject.subject_id AS subject_id,
            subject.name AS subject_name,

            topic.topic_id AS topic_id,
            topic.name AS topic_name,

            concept.concept_id AS concept_id,
            concept.title AS concept_title,
            concept.name AS concept_name,
            concept.file_path AS concept_file_path,

            document.document_id AS document_id,
            document.title AS document_title,
            document.file_path AS document_file_path,
            document.content_preview AS document_content_preview,
            document.page_start AS document_page_start,
            document.page_end AS document_page_end,
            document.order_index AS document_order_index

        ORDER BY score DESC, document_order_index ASC, document_id ASC
        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(
                cypher,
                query_keyword=query_keyword,
                raw_query=raw_query,
                normalized_query=normalized_query,
                slug_query=slug_query,
                limit=limit,
            )
            return [dict(record) for record in result]

    # Backward-compatible method name retained for older callers.
    def find_documents_by_keyword(self, query_keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        return self.search_keyword_documents(query_keyword=query_keyword, limit=limit)
