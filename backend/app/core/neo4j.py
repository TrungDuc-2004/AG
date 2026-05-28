from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j.exceptions import ClientError, Neo4jError

from app.core.config import settings

_driver: AsyncDriver | None = None


NEO4J_CONSTRAINTS = (
    "CREATE CONSTRAINT thing_name_unique IF NOT EXISTS FOR (root:Thing) REQUIRE root.thing_name IS UNIQUE",
    "CREATE CONSTRAINT class_id_unique IF NOT EXISTS FOR (c:Class) REQUIRE c.class_id IS UNIQUE",
    "CREATE CONSTRAINT subject_id_unique IF NOT EXISTS FOR (s:Subject) REQUIRE s.subject_id IS UNIQUE",
    "CREATE CONSTRAINT topic_id_unique IF NOT EXISTS FOR (t:Topic) REQUIRE t.topic_id IS UNIQUE",
    "CREATE CONSTRAINT concept_id_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.concept_id IS UNIQUE",
    "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.document_id IS UNIQUE",
    "CREATE CONSTRAINT keyword_id_unique IF NOT EXISTS FOR (k:Keyword) REQUIRE k.keyword_id IS UNIQUE",
)

NEO4J_SCHEMA_CLEANUP_QUERIES = (
    "DROP INDEX topic_bag_embedding_idx IF EXISTS",
    "DROP INDEX search_bag_embedding_idx IF EXISTS",
    "DROP CONSTRAINT topic_bag_id_unique IF EXISTS",
)

NEO4J_CLEANUP_QUERIES = (
    # Remove older design properties while preserving nodes/relationships that can be merged later.
    "MATCH (n) REMOVE n.mongo_id",
    # TopicBag and TypeDoc are no longer part of the Neo4j graph target.
    "MATCH ()-[r:HAS_TOPIC_BAG]->() DELETE r",
    "MATCH (b:TopicBag) DETACH DELETE b",
    "MATCH ()-[r:HAS_TYPE]->() DELETE r",
    "MATCH (td:TypeDoc) DETACH DELETE td",
)


def get_neo4j_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver


async def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


async def _try_create_database() -> None:
    """Create Neo4j database when supported.

    Neo4j Community usually only uses the default `neo4j` database. In that case,
    CREATE DATABASE is unsupported or unnecessary, so this function silently skips.
    """
    if settings.NEO4J_DATABASE == "neo4j":
        return
    driver = get_neo4j_driver()
    try:
        async with driver.session(database="system") as session:
            result = await session.run(
                "SHOW DATABASES YIELD name WHERE name = $name RETURN name",
                name=settings.NEO4J_DATABASE,
            )
            if await result.single():
                return
            await session.run(f"CREATE DATABASE `{settings.NEO4J_DATABASE}` IF NOT EXISTS")
    except (ClientError, Neo4jError):
        return


async def ensure_neo4j_ready() -> None:
    await _try_create_database()
    driver = get_neo4j_driver()
    async with driver.session(database=settings.NEO4J_DATABASE) as session:
        for query in NEO4J_SCHEMA_CLEANUP_QUERIES:
            try:
                await session.run(query)
            except (ClientError, Neo4jError):
                pass

        for query in NEO4J_CONSTRAINTS:
            try:
                await session.run(query)
            except (ClientError, Neo4jError):
                pass
        for query in NEO4J_CLEANUP_QUERIES:
            try:
                await session.run(query)
            except (ClientError, Neo4jError):
                pass

        # Root ontology node. All Class nodes are attached below this node by HAS_CLASS.
        await session.run(
            """
            MERGE (root:Thing {thing_name: 'STEM'})
            SET root.name = 'STEM',
                root.description = 'Root node of STEM learning knowledge graph'
            """
        )



async def neo4j_health() -> dict[str, Any]:
    try:
        await ensure_neo4j_ready()
        driver = get_neo4j_driver()
        async with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run("RETURN 1 AS ok")
            record = await result.single()
        return {"ok": bool(record and record["ok"] == 1), "database": settings.NEO4J_DATABASE}
    except Exception as exc:  # pragma: no cover - health response path
        return {"ok": False, "database": settings.NEO4J_DATABASE, "error": str(exc)}
