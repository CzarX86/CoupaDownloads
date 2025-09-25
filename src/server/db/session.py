"""Async SQLAlchemy session management."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
from weakref import WeakSet

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .config import DatabaseSettings, resolve_async_database_url

_settings = DatabaseSettings()
_engine: AsyncEngine = create_async_engine(resolve_async_database_url(_settings), echo=_settings.echo, future=True)
_async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=_engine,
    expire_on_commit=False,
)
_active_sessions: "WeakSet[AsyncSession]" = WeakSet()


@asynccontextmanager
async def async_session() -> AsyncIterator[AsyncSession]:
    """Yield a managed async session."""

    async with _async_session_factory() as session:
        _active_sessions.add(session)
        try:
            yield session
        finally:
            _active_sessions.discard(session)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency for injecting a session."""

    async with async_session() as session:
        yield session


async def close_engine() -> None:
    if _active_sessions:
        raise RuntimeError("Cannot dispose engine while sessions are still active")
    await _engine.dispose()


def get_engine() -> AsyncEngine:
    """Expose the shared async engine instance for lifecycle hooks."""

    return _engine
