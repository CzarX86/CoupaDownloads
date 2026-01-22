"""
Profile Manager Contract Definitions

This module defines the contract types and enums used by the ProfileManager.
These are simplified versions for the current implementation.
"""

from enum import Enum
from typing import List, Optional
from dataclasses import dataclass


class VerificationMethod(Enum):
    """Methods for verifying profile integrity."""
    CAPABILITY_CHECK = "capability_check"
    FILE_CHECK = "file_check"
    REGISTRY_CHECK = "registry_check"


class ProfileStatus(Enum):
    """Status of a browser profile."""
    READY = "ready"
    LOCKED = "locked"
    MISSING = "missing"
    CORRUPTED = "corrupted"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class RetryConfig:
    """Configuration for retry operations."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0


@dataclass
class VerificationConfig:
    """Configuration for profile verification."""
    enabled_methods: List[VerificationMethod]
    retry_config: RetryConfig
    timeout_seconds: float = 10.0


# Exception classes (using the ones from exceptions.py)
from EXPERIMENTAL.workers.exceptions import (
    ProfileLockedException,
    InsufficientSpaceException,
    PermissionDeniedException,
    ProfileCorruptedException,
)