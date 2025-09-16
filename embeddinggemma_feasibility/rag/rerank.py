from __future__ import annotations

from typing import List

from .retrieve import Candidate


def rerank_candidates(query: str, candidates: List[Candidate], top_k: int = 3) -> List[Candidate]:
    """Rerank candidates using a CrossEncoder (MS MARCO MiniLM-L-6-v2).

    Requires sentence-transformers; downloads model on first use.
    """
    if not candidates:
        return []

    try:
        from sentence_transformers import CrossEncoder
    except Exception as e:
        raise RuntimeError(
            "sentence-transformers is required for reranking. Install it first."
        ) from e

    model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    pairs = [(query, c.snippet) for c in candidates]
    scores = model.predict(pairs)
    scored = list(zip(candidates, map(float, scores)))
    scored.sort(key=lambda x: x[1], reverse=True)
    top = [c for c, _ in scored[:max(1, top_k)]]
    return top

