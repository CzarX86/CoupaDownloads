from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .config import RAGConfig


def build_index(
    texts: List[str],
    metadatas: Optional[List[dict]] = None,
    persist_dir: Optional[Path] = None,
    embed_model_name: Optional[str] = None,
) -> None:
    """Build and persist a vector index using HNSWLib via LlamaIndex.

    Notes
    -----
    - Imports are inside function to avoid hard dependency at import-time.
    - Persisted index appears under `persist_dir` with docstore/index/vector store files.
    """
    if not texts:
        raise ValueError("No texts provided for indexing")

    try:
        from llama_index.core import VectorStoreIndex, Document, StorageContext, Settings
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    except Exception as e:
        raise RuntimeError(
            "llama-index is required. Install it first (see requirements)."
        ) from e

    # Prefer HNSW for performance; fall back to default in-memory store if not available
    use_hnsw = False
    try:
        from llama_index.vector_stores.hnswlib import HnswlibVectorStore  # type: ignore
        use_hnsw = True
    except Exception:
        HnswlibVectorStore = None  # type: ignore

    cfg = RAGConfig()
    persist_dir = Path(persist_dir or cfg.ensure_index_dir())
    embed_model_name = embed_model_name or cfg.embed_model

    # Prepare embedding model and vector store
    embed_model = HuggingFaceEmbedding(model_name=embed_model_name)
    if use_hnsw:
        # Determine embedding dimension with a single probe
        try:
            dim = len(embed_model.get_text_embedding("dim-probe"))
        except Exception:
            # Fallback to common dims for small/sentence models
            dim = 384
        # Choose a safe capacity (HNSW index is resizable, but needs an initial cap)
        max_elements = max(1024, len(texts))
        # Build Hnswlib-backed vector store using convenience constructor
        vector_store = HnswlibVectorStore.from_params(
            space="cosine", dimension=dim, max_elements=max_elements, ef=200
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
    else:
        storage_context = StorageContext.from_defaults()

    # Convert to Documents with optional metadata
    documents = []
    if metadatas and len(metadatas) == len(texts):
        for t, m in zip(texts, metadatas):
            documents.append(Document(text=t, metadata=m))
    else:
        for t in texts:
            documents.append(Document(text=t))

    # Configure embedding model via Settings (ServiceContext is deprecated)
    prev_embed = getattr(Settings, "embed_model", None)
    try:
        Settings.embed_model = embed_model
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            show_progress=True,
        )
    finally:
        # Restore previous embed model to avoid global side-effects
        try:
            Settings.embed_model = prev_embed
        except Exception:
            pass
    index.storage_context.persist(persist_dir=str(persist_dir))


def load_index(persist_dir: Path):
    try:
        from llama_index.core import StorageContext, load_index_from_storage
    except Exception as e:
        raise RuntimeError(
            "llama-index is required to load an index."
        ) from e

    persist_dir = Path(persist_dir)
    storage_context = StorageContext.from_defaults(persist_dir=str(persist_dir))
    index = load_index_from_storage(storage_context)
    return index
