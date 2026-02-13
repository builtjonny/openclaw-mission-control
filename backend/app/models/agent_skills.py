"""Agent/skill many-to-many link rows."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel

RUNTIME_ANNOTATION_TYPES = (datetime,)


class AgentSkill(QueryModel, table=True):
    """Association row mapping one agent to one skill."""

    __tablename__ = "agent_skills"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "skill_id",
            name="uq_agent_skills_agent_id_skill_id",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agent_id: UUID = Field(foreign_key="agents.id", index=True)
    skill_id: UUID = Field(foreign_key="skills.id", index=True)
    created_at: datetime = Field(default_factory=utcnow)
