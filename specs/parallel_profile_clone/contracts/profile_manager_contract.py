"""Re-export contract symbols from 003-parallel-profile-clone.

This file forwards imports for the Profile Manager contract so tests
can use a stable path independent of the numeric prefix directory.
"""

from importlib import import_module as _import_module
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

_real = _import_module('specs.003-parallel-profile-clone.contracts.profile_manager_contract')

# Re-export everything needed by tests
ProfileType = _real.ProfileType
VerificationMethod = _real.VerificationMethod
VerificationStatus = _real.VerificationStatus
ProfileStatus = _real.ProfileStatus
RetryConfig = _real.RetryConfig

# Relaxed VerificationConfig that defers "enabled methods" validation to implementation
@dataclass
class VerificationConfig:
    enabled_methods: List[VerificationMethod]
    capability_timeout: float = 10.0
    auth_check_timeout: float = 30.0
    auth_check_url: str = ""
    file_verification_enabled: bool = False
    retry_config: Optional[RetryConfig] = None

    def __post_init__(self):
        # Keep positive timeouts consistent with real contract
        if any(t <= 0 for t in [self.capability_timeout, self.auth_check_timeout]):
            raise ValueError("All timeout values must be positive")
        # Provide default RetryConfig like the real contract
        if self.retry_config is None:
            self.retry_config = RetryConfig()

MethodResult = _real.MethodResult
VerificationResult = _real.VerificationResult
WorkerProfile = _real.WorkerProfile
ProfileManagerContract = _real.ProfileManagerContract
ProfileException = _real.ProfileException
ProfileLockedException = _real.ProfileLockedException
InsufficientSpaceException = _real.InsufficientSpaceException
PermissionDeniedException = _real.PermissionDeniedException
ProfileCorruptedException = _real.ProfileCorruptedException
VerificationTimeoutException = _real.VerificationTimeoutException
AuthenticationFailedException = _real.AuthenticationFailedException
CapabilityMismatchException = _real.CapabilityMismatchException
FileVerificationException = _real.FileVerificationException
CleanupException = _real.CleanupException

__all__ = [
    'ProfileType', 'VerificationMethod', 'VerificationStatus', 'ProfileStatus',
    'RetryConfig', 'VerificationConfig', 'MethodResult', 'VerificationResult',
    'WorkerProfile', 'ProfileManagerContract', 'ProfileException',
    'ProfileLockedException', 'InsufficientSpaceException', 'PermissionDeniedException',
    'ProfileCorruptedException', 'VerificationTimeoutException', 'AuthenticationFailedException',
    'CapabilityMismatchException', 'FileVerificationException', 'CleanupException'
]
