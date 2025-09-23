"""Entrypoint to run the PDF training FastAPI app with Uvicorn."""
from __future__ import annotations

import uvicorn

from . import app


def run() -> None:
    uvicorn.run(
        "server.pdf_training_app:app",
        host="127.0.0.1",
        port=8008,
        reload=False,
    )


if __name__ == "__main__":
    run()
