"""Async SQLAlchemy session management."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .config import DatabaseSettings, resolve_async_database_url

_settings = DatabaseSettings()
_engine: AsyncEngine = create_async_engine(resolve_async_database_url(_settings), echo=_settings.echo, future=True)
_async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=_engine,
    expire_on_commit=False,
)


@asynccontextmanager
async def async_session() -> AsyncIterator[AsyncSession]:
    """Yield a managed async session."""

    async with _async_session_factory() as session:
        yield session


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency for injecting a session."""

    async with async_session() as session:
        yield session


async def close_engine() -> None:
    await _engine.dispose()


async def reconfigure_engine(url: str) -> None:
    """Dispose the current engine and create a new one pointing to ``url``."""

    global _engine, _async_session_factory
    await _engine.dispose()
    _engine = create_async_engine(url, echo=_settings.echo, future=True)
    _async_session_factory = async_sessionmaker(bind=_engine, expire_on_commit=False)
