from __future__ import annotations

"""
RAG-assisted retrieval helpers for the advanced extractor.

Builds an in-memory LlamaIndex over document chunks and retrieves
top candidate snippets for each target field to focus downstream NLP.
"""

from typing import Dict, List, Optional, Any

from .rag.splitters import split_text
from .config import get_config


# Simple field → query mapping (can be refined over time)
FIELD_QUERIES: Dict[str, str] = {
    "contract_end_date": "contract end date OR end of agreement",
    "contract_start_date": "contract start date OR effective date",
    "contract_name": "contract name OR agreement title",
    "contract_type": "type of contract OR agreement type",
    "sow_value_eur": "SOW value in EUR OR euro amount",
    "sow_value_lc": "SOW value in local currency OR amount local",
    "fx": "exchange rate OR FX",
    "pwo_number": "PWO number OR purchase work order",
    "managed_by": "managed by OR owner",
    "platform_technology": "platform or technology",
}


def retrieve_candidates_for_fields(
    text: str,
    field_keys: List[str],
    top_k: int = 3,
) -> Dict[str, List[str]]:
    """Return top candidate snippets per field using an ephemeral index.

    Builds a small in-memory index from character chunks; avoids disk writes.
    """
    if not text or not field_keys:
        return {k: [] for k in field_keys}

    try:
        # Prefer new Settings API; avoid deprecated ServiceContext
        try:
            from llama_index.settings import Settings  # type: ignore
        except Exception:
            from llama_index.core import Settings  # type: ignore

        from llama_index.core import VectorStoreIndex, Document  # type: ignore
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # type: ignore
    except Exception:
        # If core RAG libs are unavailable, return empty results gracefully
        return {k: [] for k in field_keys}

    use_hnsw = False
    try:
        from llama_index.vector_stores.hnswlib import HnswlibVectorStore  # type: ignore
        use_hnsw = True
    except Exception:
        HnswlibVectorStore = None  # type: ignore

    chunks = split_text(text, max_chars=1000, overlap=120)
    if not chunks:
        return {k: [] for k in field_keys}

    # Build ephemeral index (new Settings-based API)
    embed_model = HuggingFaceEmbedding(model_name="intfloat/multilingual-e5-small")
    docs = [Document(text=c) for c in chunks]

    # Temporarily set global Settings for this operation
    prev_embed: Optional[Any] = None
    try:
        prev_embed = getattr(Settings, "embed_model", None)
        setattr(Settings, "embed_model", embed_model)

        if use_hnsw:
            index = VectorStoreIndex.from_documents(
                docs, show_progress=False
            )
        else:
            # Default in-memory vector store
            index = VectorStoreIndex.from_documents(
                docs, show_progress=False
            )
    finally:
        # Restore previous settings to avoid side effects
        try:
            setattr(Settings, "embed_model", prev_embed)
        except Exception:
            pass

    cfg = get_config()
    out: Dict[str, List[str]] = {}
    for key in field_keys:
        query = FIELD_QUERIES.get(key, key.replace("_", " "))
        try:
            engine = index.as_query_engine(similarity_top_k=max(1, top_k), response_mode="no_text")
            nodes = engine.retrieve(query)
        except Exception:
            retriever = index.as_retriever(similarity_top_k=max(1, top_k))
            nodes = retriever.retrieve(query)

        # Convert nodes to snippets
        def to_snippets(ns) -> List[str]:
            s: List[str] = []
            for n in ns:
                node = getattr(n, "node", None) or getattr(n, "text_node", None) or n
                txt = getattr(node, "get_content", None)
                snippet = txt() if callable(txt) else getattr(node, "text", "")
                if snippet:
                    s.append(snippet)
            return s

        snippets: List[str] = to_snippets(nodes)

        # Optional: rerank snippets using CrossEncoder
        if getattr(cfg, 'use_reranker', False):
            try:
                from .rag.retrieve import Candidate
                from .rag.rerank import rerank_candidates
                cands = [Candidate(id=str(i), score=0.0, snippet=s) for i, s in enumerate(snippets)]
                top = rerank_candidates(query, cands, top_k=max(1, top_k))
                snippets = [c.snippet for c in top]
            except Exception:
                # Keep original ordering on failure
                pass

        out[key] = snippets
    return out
