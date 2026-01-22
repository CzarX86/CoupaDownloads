"""Authentication verifier stub.

Checks session login status against configured URL; tests patch verify.
"""
from ..specs.parallel_profile_clone.contracts.profile_manager_contract import (
    VerificationConfig,
    WorkerProfile,
    MethodResult,
    VerificationMethod,
)


class AuthVerifier:
    def __init__(self, config: VerificationConfig):
        self.config = config

    def verify(self, profile: WorkerProfile) -> MethodResult:
        return MethodResult(method=VerificationMethod.AUTH_CHECK, success=True, duration_seconds=0.01)
