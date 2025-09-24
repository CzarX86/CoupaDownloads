"""FastAPI application for the AI Builder-style PDF training flow."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from hashlib import sha1
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI

from server.db import models
from server.db.config import resolve_async_database_url
from server.db.session import close_engine, _engine, reconfigure_engine

from . import api


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    original_url = os.getenv("PDF_TRAINING_DB_URL")
    test_name = os.getenv("PYTEST_CURRENT_TEST")
    new_url: str | None = None
    reset_schema = bool(test_name)

    if reset_schema and original_url and original_url.startswith("sqlite+aiosqlite:///"):
        base_path = Path(original_url.split("sqlite+aiosqlite:///", 1)[1])
        hashed = sha1(test_name.encode("utf-8")).hexdigest()
        new_path = base_path.with_name(f"{base_path.stem}-{hashed}.db")
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_url = f"sqlite+aiosqlite:///{new_path}"
        os.environ["PDF_TRAINING_DB_URL"] = new_url
        await reconfigure_engine(new_url)

    async with _engine.begin() as conn:  # type: ignore[attr-defined]
        if reset_schema:
            await conn.run_sync(models.Base.metadata.drop_all)
        await conn.run_sync(models.Base.metadata.create_all)

    try:
        yield
    finally:
        await close_engine()
        if new_url is not None:
            if original_url is None:
                os.environ.pop("PDF_TRAINING_DB_URL", None)
                await reconfigure_engine(resolve_async_database_url())
            else:
                os.environ["PDF_TRAINING_DB_URL"] = original_url
                await reconfigure_engine(original_url)


app = FastAPI(title="PDF Training Orchestrator", version="0.1.0", lifespan=_lifespan)
app.include_router(api.router, prefix="/api/pdf-training", tags=["pdf-training"])
setattr(app, "app", app)


__all__ = ["app"]
