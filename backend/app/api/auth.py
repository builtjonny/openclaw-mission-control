"""Authentication endpoints for the Mission Control API."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import col, select

from app.core.auth import AuthContext, get_auth_context
from app.core.auth_mode import AuthMode
from app.core.config import settings
from app.core.jwt import create_access_token
from app.core.logging import get_logger
from app.core.passwords import MIN_PASSWORD_LENGTH, hash_password, verify_password
from app.db.session import get_session
from app.models.organization_invites import OrganizationInvite
from app.models.users import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.users import UserRead
from app.services.organizations import accept_invite, normalize_invited_email

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


@router.post("/register", response_model=TokenResponse)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = SESSION_DEP,
) -> TokenResponse:
    """Register a new local user via an organization invite token."""
    if settings.auth_mode != AuthMode.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration is only available in local auth mode.",
        )

    if len(payload.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
        )

    # Validate invite token.
    invite = (
        await session.exec(
            select(OrganizationInvite).where(
                col(OrganizationInvite.token) == payload.invite_token.strip(),
                col(OrganizationInvite.accepted_at).is_(None),
            )
        )
    ).first()
    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite token.",
        )

    # Check email matches invite.
    email = normalize_invited_email(payload.email)
    invited_email = normalize_invited_email(invite.invited_email)
    if email != invited_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email does not match the invite.",
        )

    # Check for existing user with this email.
    existing_user = (
        await session.exec(select(User).where(func.lower(col(User.email)) == email))
    ).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists. Please log in instead.",
        )

    # Create user with local-<uuid> as clerk_user_id.
    local_user_id = f"local-{uuid4()}"
    pw_hash = hash_password(payload.password)
    user = User(
        clerk_user_id=local_user_id,
        email=email,
        name=payload.name.strip(),
        password_hash=pw_hash,
    )
    session.add(user)
    await session.flush()

    # Accept the invite (creates membership, sets active org, commits).
    await accept_invite(session, invite, user)

    token = create_access_token(
        subject=local_user_id,
        extra_claims={"email": email},
    )
    logger.info(
        "auth.local.register.success email=%s user_id=%s",
        email,
        local_user_id[-6:],
    )
    return TokenResponse(access_token=token)
