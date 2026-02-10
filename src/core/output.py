"""Utilities for controlled console output."""

from __future__ import annotations

import builtins
import os
from typing import Any, Optional

_SUPPRESS_VALUES = {"1", "true", "yes"}


def should_suppress_output() -> bool:
    """Return True when worker output should be suppressed."""
    return os.environ.get("SUPPRESS_WORKER_OUTPUT", "").strip().lower() in _SUPPRESS_VALUES


def maybe_print(*args: Any, **kwargs: Any) -> None:
    """Print only when output is not suppressed."""
    if should_suppress_output():
        return
    builtins.print(*args, **kwargs)


class OutputSuppressor:
    """Context manager to suppress console output during TUI runtime."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._orig_print: Optional[Any] = None
        self._orig_disable: Optional[int] = None
        self._structlog_config: Optional[dict] = None
        self._structlog_devnull = None

    def __enter__(self):
        if not self.enabled:
            return self
        self._orig_print = builtins.print
        builtins.print = maybe_print

        # Silence standard logging
        try:
            import logging
            self._orig_disable = logging.root.manager.disable
            logging.disable(logging.CRITICAL)
        except Exception:
            self._orig_disable = None

        # Best-effort: silence structlog output (if available)
        try:
            import structlog
            self._structlog_config = structlog.get_config()
            self._structlog_devnull = open(os.devnull, "w")
            try:
                structlog.configure(
                    processors=self._structlog_config.get("processors", []),
                    wrapper_class=self._structlog_config.get("wrapper_class"),
                    context_class=self._structlog_config.get("context_class"),
                    logger_factory=structlog.WriteLoggerFactory(file=self._structlog_devnull),
                    cache_logger_on_first_use=self._structlog_config.get("cache_logger_on_first_use", True),
                )
            except TypeError:
                # Older structlog versions may not support file=; ignore safely
                pass
        except Exception:
            self._structlog_config = None

        return self

    def __exit__(self, exc_type, exc, tb):
        if not self.enabled:
            return False
        if self._orig_print is not None:
            builtins.print = self._orig_print

        try:
            import logging
            if self._orig_disable is not None:
                logging.disable(self._orig_disable)
        except Exception:
            pass

        if self._structlog_config is not None:
            try:
                import structlog
                structlog.configure(**self._structlog_config)
            except Exception:
                pass
        if self._structlog_devnull:
            try:
                self._structlog_devnull.close()
            except Exception:
                pass
        return False
