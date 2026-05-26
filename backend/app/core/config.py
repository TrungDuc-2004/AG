import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# backend/app/core/config.py -> parents[2] = backend, parents[3] = project root
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Prefer backend/.env because this project is usually started from backend/.
# Fall back to project-root .env only when backend/.env does not exist.
# This avoids conflicting GOOGLE_DRIVE_* values when both files are present.
_CANDIDATE_ENV_FILES = [
    BACKEND_DIR / ".env",
    PROJECT_ROOT / ".env",
    BACKEND_DIR / "app" / "core" / "config.env",
]
_ENV_FILES: tuple[str, ...] = tuple(str(path) for path in _CANDIDATE_ENV_FILES if path.exists())


def _env_str(alias: str, default: str) -> str:
    """Read legacy env alias when the canonical env name is not provided."""
    return os.getenv(alias, default)


def _env_int(alias: str, default: int) -> int:
    value = os.getenv(alias)
    if value is None or value == "":
        return default
    return int(value)


class Settings(BaseSettings):
    APP_NAME: str = "STEM Learning Resources API"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "stem_learning"

    STORAGE_PROVIDER: str = "google_drive"
    STORAGE_ROOT_PREFIX: str = "STEM"

    # Google Drive auth mode:
    # oauth: recommended for local/personal Google Drive.
    # service_account: only use with Shared Drive.
    GOOGLE_DRIVE_AUTH_MODE: str = "oauth"
    GOOGLE_DRIVE_OAUTH_CLIENT_FILE: str = "./credentials/google-drive-oauth-client.json"
    GOOGLE_DRIVE_OAUTH_TOKEN_FILE: str = "./credentials/google-drive-token.json"
    GOOGLE_APPLICATION_CREDENTIALS: str = "./credentials/google-drive-service-account.json"
    GOOGLE_DRIVE_ROOT_FOLDER_ID: str = ""
    GOOGLE_DRIVE_MAKE_PUBLIC: bool = False

    # PostgreSQL sync
    POSTGRES_HOST: str = Field(default_factory=lambda: _env_str("PG_HOST", "localhost"))
    POSTGRES_PORT: int = Field(default_factory=lambda: _env_int("PG_PORT", 5432))
    POSTGRES_USER: str = Field(default_factory=lambda: _env_str("PG_USER", "postgres"))
    POSTGRES_PASSWORD: str = Field(default_factory=lambda: _env_str("PG_PASSWORD", "12345678"))
    POSTGRES_DB: str = Field(default_factory=lambda: _env_str("PG_NAME", "stem_learning_pg"))
    POSTGRES_ADMIN_DB: str = "postgres"

    # Neo4j sync
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "12345678"
    NEO4J_DATABASE: str = "neo4j"

    AUTO_SYNC_ENABLED: bool = True

    # TopicBag/vector search defaults. multilingual-e5-small returns 384-dimensional vectors.
    EMBEDDING_DIM: int = 384
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"
    AUTO_EMBED_TOPIC_BAG: bool = True

    # AI-Extract/Gemini/Kaggle options. app/services/gemini/client.py still reads
    # GEMINI_API_KEYS from app/core/config.env for key rotation compatibility.
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8101
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_MIN_INTERVAL: float = 4.5
    GEMINI_COOLDOWN_SECONDS: int = 300
    AI_EXTRACT_DEFAULT_CLASS_MAP_ID: str | None = None
    AI_EXTRACT_DEFAULT_SUBJECT_MAP_ID: str | None = None

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        extra="ignore",
    )

    @field_validator("API_PREFIX")
    @classmethod
    def normalize_api_prefix(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("/"):
            value = f"/{value}"
        return value.rstrip("/") or "/api"

    @field_validator("GOOGLE_DRIVE_AUTH_MODE")
    @classmethod
    def normalize_drive_auth_mode(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"oauth", "service_account"}:
            raise ValueError("GOOGLE_DRIVE_AUTH_MODE must be 'oauth' or 'service_account'")
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def postgres_admin_dsn(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_ADMIN_DB}"
        )

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
