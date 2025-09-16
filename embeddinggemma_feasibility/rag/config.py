from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass
class RAGConfig:
    """Configuration for the minimal RAG pipeline.

    Defaults favor local, offline-friendly behavior and small models.
    """

    index_dir: Path = Path(os.getenv("RAG_INDEX_DIR", "embeddinggemma_feasibility/data/rag_index"))
    embed_model: str = os.getenv("RAG_EMBED_MODEL", "intfloat/multilingual-e5-small")
    use_reranker: bool = os.getenv("RAG_USE_RERANKER", "0") == "1"
    top_k: int = int(os.getenv("RAG_TOP_K", "8"))
    return_k: int = int(os.getenv("RAG_RETURN_K", "3"))

    def ensure_index_dir(self) -> Path:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        return self.index_dir

