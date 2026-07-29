"""
Default configuration factories for profile management.

DEPRECATED: Use src.config.constants instead.

This module is maintained for backward compatibility. All new code should use
the centralized constants from src.config.constants.

Migration guide:
    Old: from src.config.defaults import get_default_timeouts
         timeouts = get_default_timeouts()
    
    New: from src.config.constants import TASK_COMPLETION_TIMEOUT
         timeout = TASK_COMPLETION_TIMEOUT
"""

from __future__ import annotations

import warnings
from typing import Dict, Any

# Deprecation warning
warnings.warn(
    "src.config.defaults is deprecated. "
    "Use src.config.constants for centralized constants. "
    "This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)


def get_default_profile_manager_kwargs() -> Dict[str, Any]:
    """Return safe default kwargs for ProfileManager initialization.

    These defaults are conservative and avoid platform-specific assumptions.
    Consumers can override as needed.
    """
    return {
        'base_profile_path': None,  # let the app set a path if needed
        'cleanup_on_exit': True,
        'max_profiles': 8,
        'profile_size_limit_mb': 500,
        'base_profile_name': None,
    }


def get_default_timeouts() -> Dict[str, float]:
    """Default operation timeouts in seconds for profile operations."""
    return {
        'clone_timeout': 10.0,       # time budget for cloning from base
        'verify_timeout': 5.0,       # time budget for verification (if implemented)
        'cleanup_timeout': 10.0,     # time budget for cleaning up profiles
    }


def get_default_circuit_breaker() -> Dict[str, Any]:
    """Default circuit breaker configuration for profile operations."""
    return {
        'failure_threshold': 3,      # open circuit after N consecutive failures
        'recovery_time_window': 30,  # seconds to half-open after open state
    }
