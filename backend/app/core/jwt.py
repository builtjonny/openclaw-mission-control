"""JWT token creation and decoding for local email/password auth."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import jwt

from app.core.config import settings
from app.core.time import utcnow

ALGORITHM = "HS256"
DEFAULT_EXPIRY_HOURS = 24


class JWTError(Exception):
    """Raised when JWT creation or verification fails."""


def create_access_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, object] | None = None,
) -> str:
    """Create a signed JWT access token with a subject claim."""
    now = utcnow()
    expire = now + (expires_delta or timedelta(hours=DEFAULT_EXPIRY_HOURS))
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "iss": "mission-control-local",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token. Raises JWTError on failure."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[ALGORITHM],
            issuer="mission-control-local",
        )
        return payload
    except jwt.PyJWTError as exc:
        raise JWTError(str(exc)) from exc
