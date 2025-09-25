"""FastAPI application for the AI Builder-style PDF training flow."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from server.db import models as db_models
from server.db.session import close_engine, get_engine

from . import api


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    reset_schema = bool(os.getenv("PYTEST_CURRENT_TEST"))
    engine = get_engine()

    async with engine.begin() as conn:  # type: ignore[attr-defined]
        if reset_schema:
            await conn.run_sync(db_models.Base.metadata.drop_all)
        await conn.run_sync(db_models.Base.metadata.create_all)

    try:
        yield
    finally:
        await close_engine()


app = FastAPI(title="PDF Training Orchestrator", version="0.1.0", lifespan=_lifespan)
app.include_router(api.router, prefix="/api/pdf-training", tags=["pdf-training"])


__all__ = ["app"]
