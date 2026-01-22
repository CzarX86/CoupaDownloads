"""Capability verifier stub.

Validates basic profile capability; in tests we patch its behavior.
"""
from ..specs.parallel_profile_clone.contracts.profile_manager_contract import (
    VerificationConfig,
    WorkerProfile,
    MethodResult,
    VerificationMethod,
)


class CapabilityVerifier:
    def __init__(self, config: VerificationConfig):
        self.config = config

    def verify(self, profile: WorkerProfile) -> MethodResult:
        # Minimal success by default; unit tests patch this method as needed.
        return MethodResult(method=VerificationMethod.CAPABILITY_CHECK, success=True, duration_seconds=0.01)
