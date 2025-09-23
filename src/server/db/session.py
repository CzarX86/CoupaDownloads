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
