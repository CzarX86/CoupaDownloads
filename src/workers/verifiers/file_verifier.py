"""File verifier stub.

Compares critical files; in tests, behavior is patched.
"""
from ..specs.parallel_profile_clone.contracts.profile_manager_contract import (
    VerificationConfig,
    WorkerProfile,
    MethodResult,
    VerificationMethod,
)


class FileVerifier:
    def __init__(self, config: VerificationConfig):
        self.config = config

    def verify(self, profile: WorkerProfile) -> MethodResult:
        return MethodResult(method=VerificationMethod.FILE_VERIFICATION, success=True, duration_seconds=0.01)
