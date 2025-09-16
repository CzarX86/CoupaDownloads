from __future__ import annotations

"""Lightweight cache helpers using diskcache if available."""

import hashlib
from typing import Callable, Optional, Any

try:
    import diskcache  # type: ignore
except Exception:  # pragma: no cover - optional dep
    diskcache = None  # type: ignore


def _key_for(text: str, model_id: str) -> str:
    h = hashlib.sha256()
    h.update(model_id.encode("utf-8", errors="ignore"))
    h.update(b"::")
    h.update(text.encode("utf-8", errors="ignore"))
    return h.hexdigest()


def cached_embed(text: str, model_id: str, embed_fn: Callable[[str], Any], cache_dir: Optional[str]) -> Any:
    """Return embedding using diskcache when available.

    - text: input text
    - model_id: model string to namespace the cache
    - embed_fn: function(text) -> embedding
    - cache_dir: directory for diskcache or None to disable
    """
    if not (diskcache and cache_dir):
        return embed_fn(text)

    cache = diskcache.Cache(cache_dir)
    key = _key_for(text, model_id)
    val = cache.get(key)
    if val is not None:
        return val
    val = embed_fn(text)
    try:
        cache.set(key, val, expire=None)
    except Exception:
        pass
    return val

