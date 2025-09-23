"""Database configuration helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Configuration sourced from environment variables."""

    url: Optional[str] = Field(default=None, alias="PDF_TRAINING_DB_URL")
    echo: bool = Field(default=False, alias="PDF_TRAINING_DB_ECHO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def _default_sqlite_path() -> Path:
    root = Path("storage/pdf_training").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root / "app.db"


def resolve_async_database_url(settings: DatabaseSettings | None = None) -> str:
    """Return an async database URL (defaults to SQLite + aiosqlite)."""

    settings = settings or DatabaseSettings()
    if settings.url:
        return settings.url
    sqlite_path = _default_sqlite_path()
    return f"sqlite+aiosqlite:///{sqlite_path}"


def resolve_sync_database_url(settings: DatabaseSettings | None = None) -> str:
    """Return a synchronous database URL for tooling such as Alembic."""

    settings = settings or DatabaseSettings()
    url = settings.url
    if not url:
        sqlite_path = _default_sqlite_path()
        return f"sqlite:///{sqlite_path}"
    if url.startswith("sqlite+"):
        # Alembic cannot run against the async driver directly
        return url.replace("sqlite+aiosqlite", "sqlite", 1)
    if url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg", "postgresql", 1)
    return url
