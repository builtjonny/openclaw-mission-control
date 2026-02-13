"""Authentication endpoints for the Mission Control API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import col, select

from app.core.auth import AuthContext, get_auth_context
from app.core.auth_mode import AuthMode
from app.core.config import settings
from app.core.jwt import create_access_token
from app.core.logging import get_logger
from app.core.passwords import verify_password
from app.db.session import get_session
from app.models.users import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.users import UserRead

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
AUTH_CONTEXT_DEP = Depends(get_auth_context)
SESSION_DEP = Depends(get_session)


@router.post("/bootstrap", response_model=UserRead)
async def bootstrap_user(auth: AuthContext = AUTH_CONTEXT_DEP) -> UserRead:
    """Return the authenticated user profile from token claims."""
    if auth.actor_type != "user" or auth.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return UserRead.model_validate(auth.user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = SESSION_DEP,
) -> TokenResponse:
    """Authenticate a local user with email and password, returning a JWT."""
    if settings.auth_mode != AuthMode.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email/password login is only available in local auth mode.",
        )

    email = payload.email.strip().lower()
    user = (
        await session.exec(select(User).where(func.lower(col(User.email)) == email))
    ).first()

    if user is None or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(
        subject=user.clerk_user_id,
        extra_claims={"email": user.email},
    )
    logger.info("auth.local.login.success email=%s", email)
    return TokenResponse(access_token=token)
