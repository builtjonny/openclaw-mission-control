"""Schemas for local email/password authentication endpoints."""

from __future__ import annotations

from sqlmodel import Field, SQLModel


class LoginRequest(SQLModel):
    """Email/password login payload."""

    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RegisterRequest(SQLModel):
    """Invite-based user registration payload."""

    invite_token: str = Field(min_length=1)
    email: str = Field(min_length=1)
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)


class TokenResponse(SQLModel):
    """JWT token response returned after successful login or registration."""

    access_token: str
    token_type: str = "bearer"
