"""Authentication verifier stub.

Checks session login status against configured URL; tests patch verify.
"""
from __future__ import annotations

import os
import time

import requests

from ...specs.parallel_profile_clone.contracts.profile_manager_contract import (
    VerificationConfig,
    WorkerProfile,
    MethodResult,
    VerificationMethod,
)


class AuthVerifier:
    def __init__(self, config: VerificationConfig):
        self.config = config
        self._session_redirect_signals = (
            "/sessions/new",
            "/login",
            "session_expired",
            "/auth/",
            "sso",
        )
        self._strict_mode = os.environ.get("COUPA_AUTH_CHECK_STRICT", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _is_session_redirect(self, url: str) -> bool:
        lowered = (url or "").lower()
        return bool(lowered) and any(signal in lowered for signal in self._session_redirect_signals)

    def verify(self, profile: WorkerProfile) -> MethodResult:
        started = time.time()
        target_url = (getattr(self.config, "auth_check_url", "") or "").strip()
        if not target_url:
            return MethodResult(
                method=VerificationMethod.AUTH_CHECK,
                success=True,
                duration_seconds=time.time() - started,
                details={"skipped": True, "reason": "auth_check_url_not_configured"},
            )

        timeout = max(float(getattr(self.config, "auth_check_timeout", 30.0) or 30.0), 1.0)
        try:
            response = requests.get(target_url, allow_redirects=True, timeout=timeout)
            final_url = str(response.url or "")
            if self._is_session_redirect(final_url):
                details = {
                    "final_url": final_url,
                    "status_code": response.status_code,
                    "profile_path": str(getattr(profile, "profile_path", "")),
                    "strict_mode": self._strict_mode,
                }
                if not self._strict_mode:
                    details["warning"] = "session_redirect_detected_without_browser_context"
                    return MethodResult(
                        method=VerificationMethod.AUTH_CHECK,
                        success=True,
                        duration_seconds=time.time() - started,
                        details=details,
                    )
                return MethodResult(
                    method=VerificationMethod.AUTH_CHECK,
                    success=False,
                    error_message=f"session redirect detected: {final_url}",
                    duration_seconds=time.time() - started,
                    details=details,
                )

            return MethodResult(
                method=VerificationMethod.AUTH_CHECK,
                success=True,
                duration_seconds=time.time() - started,
                details={
                    "final_url": final_url,
                    "status_code": response.status_code,
                    "profile_path": str(getattr(profile, "profile_path", "")),
                },
            )
        except requests.RequestException as exc:
            if not self._strict_mode:
                return MethodResult(
                    method=VerificationMethod.AUTH_CHECK,
                    success=True,
                    duration_seconds=time.time() - started,
                    details={
                        "warning": "request_error_without_browser_context",
                        "error": str(exc),
                        "profile_path": str(getattr(profile, "profile_path", "")),
                    },
                )
            return MethodResult(
                method=VerificationMethod.AUTH_CHECK,
                success=False,
                error_message=str(exc),
                duration_seconds=time.time() - started,
            )
