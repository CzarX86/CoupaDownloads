from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .config import RAGConfig
from .ingest import load_documents
from .index import build_index, load_index
from .retrieve import query_index
from .rerank import rerank_candidates


def _cmd_build(args: argparse.Namespace) -> None:
    cfg = RAGConfig()
    source = Path(args.source)
    persist_dir = Path(args.persist) if args.persist else cfg.ensure_index_dir()
    embed_model = args.embed_model or cfg.embed_model

    texts, metas = load_documents(source, max_chars=args.max_chars, overlap=args.overlap)
    build_index(texts, metas, persist_dir=persist_dir, embed_model_name=embed_model)
    print(f"✅ Index built and persisted to: {persist_dir}")


def _cmd_query(args: argparse.Namespace) -> None:
    cfg = RAGConfig()
    persist_dir = Path(args.index)
    index = load_index(persist_dir)

    results = query_index(index, args.q, top_k=args.top_k or cfg.top_k)
    if args.reranker or cfg.use_reranker:
        results = rerank_candidates(args.q, results, top_k=args.return_k or cfg.return_k)
    else:
        results = results[: args.return_k or cfg.return_k]

    print(json.dumps([r.model_dump() for r in results], indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(prog="rag", description="Minimal RAG utilities")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Build and persist index from a directory of docs")
    p_build.add_argument("--source", required=True, help="Directory with PDFs/txt/md")
    p_build.add_argument("--persist", help="Persist dir (default: config.index_dir)")
    p_build.add_argument("--embed-model", help="HF embedding model name")
    p_build.add_argument("--max-chars", type=int, default=1200)
    p_build.add_argument("--overlap", type=int, default=120)
    p_build.set_defaults(func=_cmd_build)

    p_query = sub.add_parser("query", help="Query a persisted index")
    p_query.add_argument("--index", required=True, help="Persisted index dir")
    p_query.add_argument("--q", required=True, help="Query text")
    p_query.add_argument("--top-k", type=int, default=None)
    p_query.add_argument("--return-k", type=int, default=None)
    p_query.add_argument("--reranker", action="store_true", help="Enable reranker")
    p_query.set_defaults(func=_cmd_query)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

