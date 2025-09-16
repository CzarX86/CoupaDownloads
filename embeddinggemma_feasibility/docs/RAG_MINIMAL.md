# RAG Minimal — Quick Start

This module adds a minimal, offline‑friendly RAG stack using LlamaIndex + HNSWLib.

Contents
- Index build: ingest PDFs/text/markdown, split into chunks, embed with a small HF model, and persist a vector index.
- Query: retrieve top‑k chunks; optional reranker via sentence-transformers CrossEncoder.

Requirements
- Python 3.12.x
- Packages (install in your active environment):
  - llama-index>=0.10
  - hnswlib>=0.8.0
  - sentence-transformers, transformers, torch (already used by the subproject)
  - pdfplumber (for PDF text extraction)

Install (subproject)
```
pip install -r embeddinggemma_feasibility/requirements.txt
```

Commands
Build index from a directory:
```
python -m embeddinggemma_feasibility.rag.cli build \
  --source embeddinggemma_feasibility/data/sample_documents \
  --persist embeddinggemma_feasibility/data/rag_index
```

Query an index:
```
python -m embeddinggemma_feasibility.rag.cli query \
  --index embeddinggemma_feasibility/data/rag_index \
  --q "Qual é o prazo de pagamento?" \
  --top-k 8 --return-k 3 --reranker
```

Configuration (env vars)
- RAG_INDEX_DIR (default: embeddinggemma_feasibility/data/rag_index)
- RAG_EMBED_MODEL (default: intfloat/multilingual-e5-small)
- RAG_USE_RERANKER ("1" to enable by default)
- RAG_TOP_K (default 8), RAG_RETURN_K (default 3)

Notes
- The text splitter is token‑agnostic (by characters) to keep usage offline.
- Reranker downloads a small CrossEncoder at first use; skip `--reranker` if fully offline.
- Index persistence includes docstore, index store and vector store files.

## Interactive mode

Prefer a guided flow? Use the interactive CLI menu:

```
poetry run python -m embeddinggemma_feasibility.interactive_cli
```

From the menu you can:
- Build index (choose source/persist/model/chunk options)
- Query index (ask a question, choose top-k/return-k, enable/disable reranker)
- Show current config (paths, defaults)

You can also run the advanced Coupa field extractor from the menu by selecting "Executar Extrator Avançado" to process PDFs and generate the CSV/relatório.

Press Enter to accept defaults shown in brackets.
