"""Helpers for validating and loading skills and agent-skill mappings."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func
from sqlmodel import col, select

from app.models.agent_skills import AgentSkill
from app.models.skills import Skill
from app.schemas.skills import SkillRef

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify_skill(value: str) -> str:
    """Build a slug from arbitrary text using lowercase alphanumeric groups."""
    slug = SLUG_RE.sub("-", value.lower()).strip("-")
    return slug or "skill"


def _dedupe_uuid_list(values: Sequence[UUID]) -> list[UUID]:
    deduped: list[UUID] = []
    seen: set[UUID] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


async def validate_skill_ids(
    session: AsyncSession,
    *,
    organization_id: UUID,
    skill_ids: Sequence[UUID],
) -> list[UUID]:
    """Validate skill IDs within an organization and return deduped IDs."""
    normalized = _dedupe_uuid_list(skill_ids)
    if not normalized:
        return []

    existing_ids = set(
        await session.exec(
            select(Skill.id)
            .where(col(Skill.organization_id) == organization_id)
            .where(col(Skill.id).in_(normalized)),
        ),
    )
    missing = [skill_id for skill_id in normalized if skill_id not in existing_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "One or more skills do not exist in this organization.",
                "missing_skill_ids": [str(skill_id) for skill_id in missing],
            },
        )
    return normalized


@dataclass(slots=True)
class SkillState:
    """Ordered skill state for an agent payload."""

    skill_ids: list[UUID] = field(default_factory=list)
    skills: list[SkillRef] = field(default_factory=list)


async def load_skill_state(
    session: AsyncSession,
    *,
    agent_ids: Sequence[UUID],
) -> dict[UUID, SkillState]:
    """Return ordered skill IDs and refs for each agent id."""
    normalized_agent_ids = _dedupe_uuid_list(agent_ids)
    if not normalized_agent_ids:
        return {}

    rows = list(
        await session.exec(
            select(
                col(AgentSkill.agent_id),
                Skill,
            )
            .join(Skill, col(Skill.id) == col(AgentSkill.skill_id))
            .where(col(AgentSkill.agent_id).in_(normalized_agent_ids))
            .order_by(
                col(AgentSkill.agent_id).asc(),
                col(AgentSkill.created_at).asc(),
            ),
        ),
    )
    state_by_agent_id: dict[UUID, SkillState] = defaultdict(SkillState)
    for agent_id, skill in rows:
        if agent_id is None:
            continue
        state = state_by_agent_id[agent_id]
        state.skill_ids.append(skill.id)
        state.skills.append(
            SkillRef(
                id=skill.id,
                name=skill.name,
                slug=skill.slug,
            ),
        )
    return dict(state_by_agent_id)


async def replace_agent_skills(
    session: AsyncSession,
    *,
    agent_id: UUID,
    skill_ids: Sequence[UUID],
) -> None:
    """Replace all skill-assignment rows for an agent."""
    normalized = _dedupe_uuid_list(skill_ids)
    await session.exec(
        delete(AgentSkill).where(
            col(AgentSkill.agent_id) == agent_id,
        ),
    )
    for skill_id in normalized:
        session.add(AgentSkill(agent_id=agent_id, skill_id=skill_id))


async def get_skill_instructions(
    session: AsyncSession,
    *,
    agent_id: UUID,
) -> list[tuple[str, str]]:
    """Return (slug, instructions) for all skills assigned to an agent.

    Only includes skills that have non-empty instructions.
    Used during agent provisioning to push SKILL_*.md files.
    """
    rows = list(
        await session.exec(
            select(Skill.slug, Skill.instructions)
            .join(AgentSkill, col(AgentSkill.skill_id) == col(Skill.id))
            .where(col(AgentSkill.agent_id) == agent_id)
            .where(col(Skill.instructions).is_not(None))
            .order_by(col(AgentSkill.created_at).asc()),
        ),
    )
    return [(slug, instructions) for slug, instructions in rows if instructions]


async def agent_counts_for_skills(
    session: AsyncSession,
    *,
    skill_ids: Sequence[UUID],
) -> dict[UUID, int]:
    """Return count of assigned agents per skill id."""
    normalized = _dedupe_uuid_list(skill_ids)
    if not normalized:
        return {}
    rows = list(
        await session.exec(
            select(
                col(AgentSkill.skill_id),
                func.count(col(AgentSkill.agent_id)),
            )
            .where(col(AgentSkill.skill_id).in_(normalized))
            .group_by(col(AgentSkill.skill_id)),
        ),
    )
    return {skill_id: int(count or 0) for skill_id, count in rows}
