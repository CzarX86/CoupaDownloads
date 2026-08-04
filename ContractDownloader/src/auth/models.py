from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class AuthState(StrEnum):
    """Outcome of a cached-session check.

    ``UNAVAILABLE`` is deliberately different from ``EXPIRED``. A temporary
    network/Coupa outage must not make the application discard a potentially
    usable bearer session.
    """

    VALID = "valid"
    MISSING = "missing"
    EXPIRED = "expired"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class SessionCheck:
    """Immutable result shared by the GUI and CLI authentication paths."""

    state: AuthState
    message: str = ""
    cookies: Mapping[str, str] = field(default_factory=dict)
    source: str = "none"

    @property
    def authenticated(self) -> bool:
        return self.state is AuthState.VALID

    @property
    def has_cached_session(self) -> bool:
        return bool(self.cookies.get("_coupa_session"))

    def with_cookies(self, cookies: Mapping[str, str], *, source: str | None = None) -> "SessionCheck":
        return SessionCheck(
            state=self.state,
            message=self.message,
            cookies=dict(cookies),
            source=source or self.source,
        )
