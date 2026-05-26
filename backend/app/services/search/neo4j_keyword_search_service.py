from typing import Any

from embedding_utils import cosine_similarity
from neo4j import GraphDatabase


class Neo4jKeywordSearchService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def search_topic_bags(self, query_embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
        """
        Search keyword giống code mẫu:
        keyword query embedding -> vector search TopicBag -> Topic candidate.

        TopicBag được tạo bằng cách gom keyword từ:
        Topic -> Concept -> Document -> Keyword.
        """
        with self.driver.session() as session:
            try:
                return self._vector_search_topic_bags(session, query_embedding, limit)
            except Exception as exc:
                print(f"[keyword-search] Vector search fallback because: {exc}")
                return self._python_fallback_search_topic_bags(session, query_embedding, limit)

    def find_documents_by_topic_and_keyword(
        self,
        topic_id: str,
        keyword_id: str,
        topic_score: float,
        matched_query_keyword: str,
        matched_keyword_name: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Sau khi match keyword thật trong TopicBag, dùng keyword_id để lấy Document thật.

        Tương đương code mẫu:
        keyword_id -> chunk_keyword -> chunk -> rebuild lesson/topic/subject.

        Bản của mình:
        keyword_id -> Document-HAS_KEYWORD->Keyword -> Document -> Concept -> Topic -> Subject.
        """
        cypher = """
        MATCH (subject:Subject)-[:HAS_TOPIC]->(topic:Topic {topic_id: $topic_id})
        MATCH (topic)-[:HAS_CONCEPT]->(concept:Concept)
        MATCH (concept)-[:HAS_DOCUMENT]->(document:Document)
        MATCH (document)-[:HAS_KEYWORD]->(keyword:Keyword {keyword_id: $keyword_id})

        OPTIONAL MATCH (document)-[:HAS_KEYWORD]->(doc_kw:Keyword)

        WITH
            subject,
            topic,
            concept,
            document,
            keyword,
            collect(DISTINCT doc_kw.keyword_name) AS document_keywords,
            collect(DISTINCT doc_kw.aliases) AS document_keyword_alias_groups

        RETURN
            $topic_score AS score,
            'exact_keyword' AS match_type,
            $matched_query_keyword AS matched_query_keyword,
            $matched_keyword_name AS matched_keyword_name,
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

        ORDER BY document_order_index ASC, document_id ASC
        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(
                cypher,
                topic_id=topic_id,
                keyword_id=keyword_id,
                topic_score=topic_score,
                matched_query_keyword=matched_query_keyword,
                matched_keyword_name=matched_keyword_name,
                limit=limit,
            )
            return [dict(record) for record in result]

    def _vector_search_topic_bags(self, session, query_embedding: list[float], limit: int) -> list[dict[str, Any]]:
        cypher = """
        CALL db.index.vector.queryNodes('topic_bag_embedding_idx', $limit, $embedding)
        YIELD node AS bag, score

        MATCH (topic:Topic)-[:HAS_TOPIC_BAG]->(bag)
        MATCH (subject:Subject)-[:HAS_TOPIC]->(topic)

        RETURN
            score,
            bag.topic_bag_id AS topic_bag_id,
            bag.embedding_text AS topic_bag_text,
            bag.keyword_ids AS keyword_ids,
            bag.keyword_names AS keyword_names,
            bag.normalized_names AS normalized_names,
            bag.aliases AS aliases,
            bag.keyword_alias_pairs AS keyword_alias_pairs,
            bag.document_ids AS topic_bag_document_ids,

            subject.subject_id AS subject_id,
            subject.name AS subject_name,

            topic.topic_id AS topic_id,
            topic.name AS topic_name

        ORDER BY score DESC
        LIMIT $limit
        """
        result = session.run(cypher, embedding=query_embedding, limit=limit)
        return [dict(record) for record in result]

    def _python_fallback_search_topic_bags(self, session, query_embedding: list[float], limit: int) -> list[dict[str, Any]]:
        cypher = """
        MATCH (topic:Topic)-[:HAS_TOPIC_BAG]->(bag:TopicBag)
        MATCH (subject:Subject)-[:HAS_TOPIC]->(topic)

        RETURN
            bag.embedding AS embedding,
            bag.topic_bag_id AS topic_bag_id,
            bag.embedding_text AS topic_bag_text,
            bag.keyword_ids AS keyword_ids,
            bag.keyword_names AS keyword_names,
            bag.normalized_names AS normalized_names,
            bag.aliases AS aliases,
            bag.keyword_alias_pairs AS keyword_alias_pairs,
            bag.document_ids AS topic_bag_document_ids,

            subject.subject_id AS subject_id,
            subject.name AS subject_name,

            topic.topic_id AS topic_id,
            topic.name AS topic_name
        """
        rows: list[dict[str, Any]] = []
        for record in session.run(cypher):
            item = dict(record)
            item["score"] = cosine_similarity(query_embedding, item.get("embedding") or [])
            item.pop("embedding", None)
            rows.append(item)

        rows.sort(key=lambda x: x.get("score", 0), reverse=True)
        return rows[:limit]
