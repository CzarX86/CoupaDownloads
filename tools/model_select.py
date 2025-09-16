#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List

from tools.model_registry import find_models


PKG_ROOT = Path(__file__).resolve().parents[1] / 'embeddinggemma_feasibility'
MODELS_DIR = PKG_ROOT / 'models'
CURRENT_LINK = MODELS_DIR / 'current'


def cmd_list(args: argparse.Namespace) -> None:
    models = find_models([str(MODELS_DIR)])
    if not models:
        print("(no models found)")
        return
    print("# Available models (newest first)\n")
    for m in models:
        tags = m.tags or {}
        dim = m.dim if m.dim is not None else "?"
        print(f"- {m.name}")
        print(f"  path: {m.path}")
        print(f"  size_mb: {m.size_mb}")
        print(f"  dim: {dim}")
        if tags:
            print(f"  tags: {json.dumps(tags)}")
        print("")


def cmd_show(args: argparse.Namespace) -> None:
    try:
        from embeddinggemma_feasibility.config import get_config
        cfg = get_config()
        active = cfg.embed_model_custom_path
    except Exception:
        active = None
    link = None
    try:
        if CURRENT_LINK.exists():
            link = str(CURRENT_LINK.resolve())
    except Exception:
        pass
    print(json.dumps({"embed_model_custom_path": active, "models_current_symlink": link}, indent=2))


def _set_symlink(target: str) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    tgt = Path(target)
    if not tgt.exists() or not tgt.is_dir():
        raise SystemExit(f"Invalid model dir: {target}")
    if CURRENT_LINK.exists() or CURRENT_LINK.is_symlink():
        try:
            CURRENT_LINK.unlink()
        except Exception:
            pass
    try:
        CURRENT_LINK.symlink_to(tgt)
    except Exception:
        # Windows fallback: write a marker file
        (MODELS_DIR / 'ACTIVE_MODEL_PATH.txt').write_text(str(tgt), encoding='utf-8')


def cmd_set_active(args: argparse.Namespace) -> None:
    _set_symlink(args.path)
    # Also hint how to set embed_model_custom_path in the running process
    print("✅ Active model symlink updated at 'embeddinggemma_feasibility/models/current'")
    print("To use it immediately in Python, call:")
    print("  from embeddinggemma_feasibility.config import update_config")
    print(f"  update_config(embed_model_custom_path=\"{args.path}\")")


def cmd_clear_active(args: argparse.Namespace) -> None:
    try:
        if CURRENT_LINK.exists() or CURRENT_LINK.is_symlink():
            CURRENT_LINK.unlink()
    except Exception:
        pass
    marker = MODELS_DIR / 'ACTIVE_MODEL_PATH.txt'
    if marker.exists():
        try:
            marker.unlink()
        except Exception:
            pass
    print("✅ Active model cleared (defaults will be used)")


def main() -> None:
    parser = argparse.ArgumentParser(description='Model selection utility')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_list = sub.add_parser('list', help='List available models with metadata')
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser('show-active', help='Show active model from config and current symlink')
    p_show.set_defaults(func=cmd_show)

    p_set = sub.add_parser('set-active', help='Set active model by creating/updating models/current symlink')
    p_set.add_argument('--path', required=True, help='Path to a Sentence Transformers model directory')
    p_set.set_defaults(func=cmd_set_active)

    p_clear = sub.add_parser('clear-active', help='Clear active model (remove symlink/marker)')
    p_clear.set_defaults(func=cmd_clear_active)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()

