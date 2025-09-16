#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class ModelInfo:
    name: str
    path: str
    mtime: float
    size_mb: float
    dim: Optional[int] = None
    tags: Optional[dict] = None


def _dir_size_mb(path: Path) -> float:
    total = 0
    for p in path.rglob('*'):
        if p.is_file():
            try:
                total += p.stat().st_size
            except Exception:
                pass
    return round(total / (1024 * 1024), 2)


def _load_dim_from_st(model_dir: Path) -> Optional[int]:
    # Try common sentence-transformers metadata locations
    # 1) modules.json + 0_Pooling/*config.json
    try:
        modules = model_dir / 'modules.json'
        if modules.exists():
            try:
                data = json.loads(modules.read_text(encoding='utf-8'))
                # look for Pooling module config
                for m in data:
                    if 'path' in m and 'Pooling' in m.get('type', ''):
                        cfile = model_dir / m['path'] / 'config.json'
                        if cfile.exists():
                            c = json.loads(cfile.read_text(encoding='utf-8'))
                            dim = c.get('word_embedding_dimension') or c.get('pooling_output_dimension')
                            if isinstance(dim, int):
                                return dim
            except Exception:
                pass
    except Exception:
        pass
    # 2) sentence_bert_config.json fallback
    try:
        sbcfg = model_dir / 'sentence_bert_config.json'
        if sbcfg.exists():
            c = json.loads(sbcfg.read_text(encoding='utf-8'))
            dim = c.get('pooling_output_dimension') or c.get('word_embedding_dimension')
            if isinstance(dim, int):
                return dim
    except Exception:
        pass
    return None


def _load_tags(model_dir: Path) -> Optional[dict]:
    # Our custom metadata if present
    for fname in ('contract_config.json', 'model_config.json'):
        f = model_dir / fname
        if f.exists():
            try:
                return json.loads(f.read_text(encoding='utf-8'))
            except Exception:
                return None
    return None


def find_models(search_dirs: List[str] | None = None) -> List[ModelInfo]:
    if not search_dirs:
        # default: under package models dir
        base = Path(__file__).resolve().parents[1] / 'embeddinggemma_feasibility' / 'models'
        search_dirs = [str(base)]

    out: List[ModelInfo] = []
    for d in search_dirs:
        p = Path(d)
        if not p.exists() or not p.is_dir():
            continue
        for sub in p.iterdir():
            if not sub.is_dir():
                continue
            try:
                stat = sub.stat()
                info = ModelInfo(
                    name=sub.name,
                    path=str(sub.resolve()),
                    mtime=stat.st_mtime,
                    size_mb=_dir_size_mb(sub),
                    dim=_load_dim_from_st(sub),
                    tags=_load_tags(sub),
                )
                out.append(info)
            except Exception:
                continue
    # newest first
    out.sort(key=lambda m: m.mtime, reverse=True)
    return out


if __name__ == '__main__':
    models = [asdict(m) for m in find_models()]
    print(json.dumps(models, indent=2))

