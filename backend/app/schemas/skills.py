"""Schemas for skill CRUD and ClawHub import payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import field_validator, model_validator
from sqlmodel import SQLModel

from app.schemas.common import NonEmptyStr

RUNTIME_ANNOTATION_TYPES = (datetime, UUID, NonEmptyStr)


class SkillBase(SQLModel):
    """Shared skill fields for create/read payloads."""

    name: str
    slug: str
    summary: str | None = None
    instructions: str | None = None
    source: str = "custom"
    category: str | None = None


class SkillRef(SQLModel):
    """Compact skill representation embedded in agent payloads."""

    id: UUID
    name: str
    slug: str


class SkillCreate(SQLModel):
    """Payload for creating a custom skill."""

    name: NonEmptyStr
    slug: str | None = None
    summary: str | None = None
    instructions: str | None = None
    category: str | None = None

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: object) -> object | None:
        """Treat empty slug strings as unset so API can auto-generate."""
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value

    @field_validator("instructions", "summary", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object | None:
        """Normalize blank text to null."""
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class SkillUpdate(SQLModel):
    """Payload for partial skill updates."""

    name: NonEmptyStr | None = None
    slug: str | None = None
    summary: str | None = None
    instructions: str | None = None
    category: str | None = None

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: object) -> object | None:
        """Treat empty slug strings as unset so API can auto-generate."""
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value

    @field_validator("instructions", "summary", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object | None:
        """Normalize blank text to null."""
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="after")
    def require_some_update(self) -> Self:
        """Reject empty update payloads to avoid no-op patch calls."""
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        return self


class SkillRead(SkillBase):
    """Skill payload returned from API endpoints."""

    id: UUID
    organization_id: UUID
    clawhub_slug: str | None = None
    clawhub_version: str | None = None
    clawhub_metadata: dict[str, Any] | None = None
    agent_count: int = 0
    created_at: datetime
    updated_at: datetime


class ClawHubImport(SQLModel):
    """Payload for importing a skill from ClawHub."""

    clawhub_slug: NonEmptyStr
    name: str | None = None
    category: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object | None:
        """Normalize blank name to null (use ClawHub displayName as fallback)."""
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class ClawHubSearchResult(SQLModel):
    """Single result from a ClawHub search."""

    slug: str | None = None
    display_name: str | None = None
    summary: str | None = None
    version: str | None = None
    score: float = 0.0
    updated_at: int | None = None


class ClawHubSkillDetail(SQLModel):
    """Skill detail fetched from ClawHub."""

    slug: str
    display_name: str
    summary: str | None = None
    tags: dict[str, str] | None = None
    stats: dict[str, Any] | None = None
    latest_version: str | None = None
    latest_changelog: str | None = None
    owner_handle: str | None = None
    owner_display_name: str | None = None


class AgentSkillsUpdate(SQLModel):
    """Payload for replacing an agent's skill assignments."""

    skill_ids: list[UUID]
