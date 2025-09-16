from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel


class Candidate(BaseModel):
    id: str
    score: float
    snippet: str
    source_path: Optional[str] = None
    chunk_idx: Optional[int] = None


def query_index(index, query: str, top_k: int = 8) -> List[Candidate]:
    """Run a similarity query against a loaded index.

    Returns a list of Candidate models with metadata where available.
    """
    if not query:
        return []

    try:
        query_engine = index.as_query_engine(similarity_top_k=top_k, response_mode="no_text")
        # Some versions expose retriever/search separately; using query engine here for simplicity.
        nodes = query_engine.retrieve(query)
    except Exception:
        # Fallback: direct retriever (if present)
        retriever = index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)

    results: List[Candidate] = []
    for n in nodes:
        # LlamaIndex NodeWithScore style
        score = float(getattr(n, "score", 0.0) or 0.0)
        node = getattr(n, "node", None) or getattr(n, "text_node", None) or n
        text = getattr(node, "get_content", None)
        snippet = text() if callable(text) else getattr(node, "text", "")
        meta = getattr(node, "metadata", {}) or {}
        results.append(
            Candidate(
                id=str(getattr(node, "node_id", getattr(node, "id_,", "")) or ""),
                score=score,
                snippet=snippet[:500],
                source_path=meta.get("source_path"),
                chunk_idx=meta.get("chunk_idx"),
            )
        )
    return results

