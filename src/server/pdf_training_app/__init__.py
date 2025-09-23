"""FastAPI application for the AI Builder-style PDF training flow."""
from __future__ import annotations

from fastapi import FastAPI

from server.db.session import close_engine

from . import api

app = FastAPI(title="PDF Training Orchestrator", version="0.1.0")
app.include_router(api.router, prefix="/api/pdf-training", tags=["pdf-training"])


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await close_engine()


__all__ = ["app"]
