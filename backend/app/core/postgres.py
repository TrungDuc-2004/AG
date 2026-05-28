import re
from typing import Any

import asyncpg

from app.core.config import settings

_pg_pool: asyncpg.Pool | None = None


def _quote_ident(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError(f"Invalid PostgreSQL identifier: {identifier!r}")
    return f'"{identifier}"'


# PostgreSQL schema aligned with the provided migration files.
# All business IDs are VARCHAR(100), not INTEGER/BIGSERIAL.
SCHEMA_SQL = """
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- TOPIC_BAG was removed from the PostgreSQL target schema.
-- Drop it during target initialization so old development tables do not remain.
DROP TABLE IF EXISTS TOPIC_BAG CASCADE;

CREATE TABLE IF NOT EXISTS SUBJECT (
    subject_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS CLASS (
    class_id VARCHAR(100) PRIMARY KEY,
    grade INTEGER,
    section VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS TYPEDOC (
    typedoc_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS TOPIC (
    topic_id VARCHAR(100) PRIMARY KEY,
    subject_id VARCHAR(100) NOT NULL REFERENCES SUBJECT(subject_id),
    name VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS CONCEPT (
    concept_id VARCHAR(100) PRIMARY KEY,
    topic_id VARCHAR(100) NOT NULL REFERENCES TOPIC(topic_id),
    name VARCHAR(255),
    definition TEXT,
    file_path VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ROLES (
    role_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "USER" (
    user_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255),
    birth_date DATE,
    role_id VARCHAR(100) NOT NULL REFERENCES ROLES(role_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS DOCUMENT (
    document_id VARCHAR(100) PRIMARY KEY,
    title VARCHAR(255),
    file_path VARCHAR(500),
    keysearch TEXT,
    topic_id VARCHAR(100) NOT NULL REFERENCES TOPIC(topic_id),
    metadata_id VARCHAR(255),
    content_preview TEXT,
    order_index INTEGER,
    page_start INTEGER,
    page_end INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS CLASS_SUBJECT (
    class_id VARCHAR(100) NOT NULL REFERENCES CLASS(class_id),
    subject_id VARCHAR(100) NOT NULL REFERENCES SUBJECT(subject_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (class_id, subject_id)
);

CREATE TABLE IF NOT EXISTS DOC_CONCEPT (
    concept_id VARCHAR(100) NOT NULL REFERENCES CONCEPT(concept_id),
    document_id VARCHAR(100) NOT NULL REFERENCES DOCUMENT(document_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (concept_id, document_id)
);

CREATE TABLE IF NOT EXISTS DOC_TYPE (
    document_id VARCHAR(100) NOT NULL REFERENCES DOCUMENT(document_id),
    typedoc_id VARCHAR(100) NOT NULL REFERENCES TYPEDOC(typedoc_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (document_id, typedoc_id)
);

CREATE TABLE IF NOT EXISTS LOG (
    log_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL REFERENCES "USER"(user_id),
    doc_id VARCHAR(100) NOT NULL REFERENCES DOCUMENT(document_id),
    action VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS KEYWORD (
    keyword_id VARCHAR(100) PRIMARY KEY,
    keyword_name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255),
    aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS DOCUMENT_KEYWORD (
    document_id VARCHAR(100) NOT NULL REFERENCES DOCUMENT(document_id),
    keyword_id VARCHAR(100) NOT NULL REFERENCES KEYWORD(keyword_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (document_id, keyword_id)
);


CREATE INDEX IF NOT EXISTS idx_topic_subject_id ON TOPIC(subject_id);
CREATE INDEX IF NOT EXISTS idx_concept_topic_id ON CONCEPT(topic_id);
CREATE INDEX IF NOT EXISTS idx_document_topic_id ON DOCUMENT(topic_id);
CREATE INDEX IF NOT EXISTS idx_doc_concept_document_id ON DOC_CONCEPT(document_id);
CREATE INDEX IF NOT EXISTS idx_document_keyword_keyword_id ON DOCUMENT_KEYWORD(keyword_id);
"""

# If the app previously created the old BIGSERIAL schema, drop only the sync target
# tables. MongoDB remains the source of truth and can re-sync data.
DROP_LEGACY_SCHEMA_SQL = """
DROP TABLE IF EXISTS TOPIC_BAG CASCADE;
DROP TABLE IF EXISTS DOCUMENT_KEYWORD CASCADE;
DROP TABLE IF EXISTS KEYWORD CASCADE;
DROP TABLE IF EXISTS LOG CASCADE;
DROP TABLE IF EXISTS DOC_TYPE CASCADE;
DROP TABLE IF EXISTS DOC_CONCEPT CASCADE;
DROP TABLE IF EXISTS CLASS_SUBJECT CASCADE;
DROP TABLE IF EXISTS DOCUMENT CASCADE;
DROP TABLE IF EXISTS CONCEPT CASCADE;
DROP TABLE IF EXISTS TOPIC CASCADE;
DROP TABLE IF EXISTS "USER" CASCADE;
DROP TABLE IF EXISTS APP_USER CASCADE;
DROP TABLE IF EXISTS ROLES CASCADE;
DROP TABLE IF EXISTS TYPEDOC CASCADE;
DROP TABLE IF EXISTS CLASS CASCADE;
DROP TABLE IF EXISTS SUBJECT CASCADE;
DROP TABLE IF EXISTS SEARCH_BAG CASCADE;
"""

TRIGGER_SQL = """
DO $$ BEGIN
    CREATE TRIGGER trg_subject_updated_at BEFORE UPDATE ON SUBJECT FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_class_updated_at BEFORE UPDATE ON CLASS FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_typedoc_updated_at BEFORE UPDATE ON TYPEDOC FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_topic_updated_at BEFORE UPDATE ON TOPIC FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_concept_updated_at BEFORE UPDATE ON CONCEPT FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_roles_updated_at BEFORE UPDATE ON ROLES FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_user_updated_at BEFORE UPDATE ON "USER" FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_document_updated_at BEFORE UPDATE ON DOCUMENT FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_class_subject_updated_at BEFORE UPDATE ON CLASS_SUBJECT FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_doc_concept_updated_at BEFORE UPDATE ON DOC_CONCEPT FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_doc_type_updated_at BEFORE UPDATE ON DOC_TYPE FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_log_updated_at BEFORE UPDATE ON LOG FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_keyword_updated_at BEFORE UPDATE ON KEYWORD FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TRIGGER trg_document_keyword_updated_at BEFORE UPDATE ON DOCUMENT_KEYWORD FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
"""


async def ensure_postgres_database() -> None:
    conn = await asyncpg.connect(settings.postgres_admin_dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            settings.POSTGRES_DB,
        )
        if not exists:
            await conn.execute(f"CREATE DATABASE {_quote_ident(settings.POSTGRES_DB)}")
    finally:
        await conn.close()


async def _drop_legacy_schema_if_needed(conn: asyncpg.Connection) -> None:
    data_type = await conn.fetchval(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'class'
          AND column_name = 'class_id'
        """
    )
    if data_type and data_type not in {"character varying", "text"}:
        await conn.execute(DROP_LEGACY_SCHEMA_SQL)


async def get_pg_pool() -> asyncpg.Pool:
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = await asyncpg.create_pool(settings.postgres_dsn, min_size=1, max_size=10)
    return _pg_pool


async def ensure_postgres_ready() -> None:
    await ensure_postgres_database()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await _drop_legacy_schema_if_needed(conn)
        await conn.execute(SCHEMA_SQL)
        await conn.execute(TRIGGER_SQL)


async def close_pg_pool() -> None:
    global _pg_pool
    if _pg_pool is not None:
        await _pg_pool.close()
        _pg_pool = None


async def postgres_health() -> dict[str, Any]:
    try:
        await ensure_postgres_ready()
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            value = await conn.fetchval("SELECT 1")
        return {"ok": value == 1, "database": settings.POSTGRES_DB}
    except Exception as exc:  # pragma: no cover - health response path
        return {"ok": False, "database": settings.POSTGRES_DB, "error": str(exc)}
