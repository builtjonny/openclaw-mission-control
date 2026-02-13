"""Skill model for organization-scoped agent capability catalog."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text, UniqueConstraint
from sqlmodel import Field

from app.core.time import utcnow
from app.models.tenancy import TenantScoped

RUNTIME_ANNOTATION_TYPES = (datetime,)


class Skill(TenantScoped, table=True):
    """Organization-scoped skill that can be assigned to agents."""

    __tablename__ = "skills"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "slug",
            name="uq_skills_organization_id_slug",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    name: str
    slug: str = Field(index=True)
    summary: str | None = None
    instructions: str | None = Field(default=None, sa_column=Column(Text))
    source: str = Field(default="custom")
    clawhub_slug: str | None = Field(default=None, index=True)
    clawhub_version: str | None = None
    clawhub_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON),
    )
    category: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
