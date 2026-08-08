"""Application settings, loaded from environment / .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend/.env
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    PROJECT_NAME: str = "ApplyFlow"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    # Separate from DEBUG: echoing every statement makes test output unreadable,
    # and DEBUG is otherwise useful to leave on during development.
    SQL_ECHO: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ---- Database ----
    DATABASE_URL: str

    # ---- Auth ----
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- CORS ----
    CORS_ORIGINS: str = "http://localhost:3000"

    # ---- Timezone ----
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # ---- Uploads ----
    MAX_UPLOAD_SIZE_MB: int = 5
    ALLOWED_UPLOAD_TYPES: str = "application/pdf"
    UPLOAD_DIR: str = "./uploads"

    # ---- AI ----
    AI_PROVIDER: Literal["mock", "ollama"] = "mock"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    @field_validator("JWT_SECRET")
    @classmethod
    def _reject_placeholder_secret(cls, v: str) -> str:
        if v.startswith("replace-me") or len(v) < 32:
            raise ValueError(
                "JWT_SECRET is unset or too short. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        return v

    @property
    def sqlalchemy_url(self) -> str:
        """Neon hands out `postgresql://`; SQLAlchemy needs the psycopg3 driver
        named explicitly, otherwise it reaches for psycopg2 and fails."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_upload_types_list(self) -> list[str]:
        return [t.strip() for t in self.ALLOWED_UPLOAD_TYPES.split(",") if t.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is read once per process."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
