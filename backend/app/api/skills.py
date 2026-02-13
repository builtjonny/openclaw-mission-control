"""Skill directory CRUD endpoints and ClawHub proxy for the organization."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import col, select

from app.api.deps import require_org_admin, require_org_member
from app.core.time import utcnow
from app.db import crud
from app.db.pagination import paginate
from app.db.session import get_session
from app.models.agent_skills import AgentSkill
from app.models.skills import Skill
from app.schemas.common import OkResponse
from app.schemas.pagination import DefaultLimitOffsetPage
from app.schemas.skills import (
    ClawHubImport,
    ClawHubSearchResult,
    ClawHubSkillDetail,
    SkillCreate,
    SkillRead,
    SkillUpdate,
)
from app.services import clawhub
from app.services.organizations import OrganizationContext
from app.services.skills import agent_counts_for_skills, slugify_skill

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastapi_pagination.limit_offset import LimitOffsetPage
    from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter(prefix="/skills", tags=["skills"])
SESSION_DEP = Depends(get_session)
ORG_MEMBER_DEP = Depends(require_org_member)
ORG_ADMIN_DEP = Depends(require_org_admin)


def _normalize_slug(slug: str | None, *, fallback_name: str) -> str:
    source = (slug or "").strip() or fallback_name
    return slugify_skill(source)


async def _require_org_skill(
    session: AsyncSession,
    *,
    skill_id: UUID,
    ctx: OrganizationContext,
) -> Skill:
    skill = await Skill.objects.by_id(skill_id).first(session)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if skill.organization_id != ctx.organization.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return skill


async def _ensure_slug_available(
    session: AsyncSession,
    *,
    organization_id: UUID,
    slug: str,
    exclude_skill_id: UUID | None = None,
) -> None:
    existing = await Skill.objects.filter_by(
        organization_id=organization_id, slug=slug
    ).first(session)
    if existing is None:
        return
    if exclude_skill_id is not None and existing.id == exclude_skill_id:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Skill slug already exists in this organization.",
    )


async def _skill_read_page(
    *,
    session: AsyncSession,
    items: Sequence[Skill],
) -> list[SkillRead]:
    if not items:
        return []
    counts = await agent_counts_for_skills(
        session,
        skill_ids=[item.id for item in items],
    )
    return [
        SkillRead.model_validate(item, from_attributes=True).model_copy(
            update={"agent_count": counts.get(item.id, 0)},
        )
        for item in items
    ]


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=DefaultLimitOffsetPage[SkillRead])
async def list_skills(
    source: str | None = None,
    category: str | None = None,
    q: str | None = None,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_MEMBER_DEP,
) -> LimitOffsetPage[SkillRead]:
    """List skills for the active organization with optional filters."""
    statement = select(Skill).where(col(Skill.organization_id) == ctx.organization.id)
    if source:
        statement = statement.where(col(Skill.source) == source)
    if category:
        statement = statement.where(col(Skill.category) == category)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            col(Skill.name).ilike(pattern) | col(Skill.summary).ilike(pattern)
        )
    statement = statement.order_by(
        func.lower(col(Skill.name)).asc(),
        col(Skill.created_at).asc(),
    )

    async def _transform(items: Sequence[object]) -> Sequence[object]:
        skills: list[Skill] = []
        for item in items:
            if not isinstance(item, Skill):
                msg = "Expected Skill items from paginated query"
                raise TypeError(msg)
            skills.append(item)
        return await _skill_read_page(session=session, items=skills)

    return await paginate(session, statement, transformer=_transform)


@router.post("", response_model=SkillRead)
async def create_skill(
    payload: SkillCreate,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> SkillRead:
    """Create a custom skill within the active organization."""
    slug = _normalize_slug(payload.slug, fallback_name=payload.name)
    await _ensure_slug_available(
        session,
        organization_id=ctx.organization.id,
        slug=slug,
    )
    skill = await crud.create(
        session,
        Skill,
        organization_id=ctx.organization.id,
        name=payload.name,
        slug=slug,
        summary=payload.summary,
        instructions=payload.instructions,
        source="custom",
        category=payload.category,
    )
    return SkillRead.model_validate(skill, from_attributes=True)


@router.get("/{skill_id}", response_model=SkillRead)
async def get_skill(
    skill_id: UUID,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_MEMBER_DEP,
) -> SkillRead:
    """Get a single skill in the active organization."""
    skill = await _require_org_skill(session, skill_id=skill_id, ctx=ctx)
    count = (
        await session.exec(
            select(func.count(col(AgentSkill.agent_id))).where(
                col(AgentSkill.skill_id) == skill.id,
            ),
        )
    ).one()
    return SkillRead.model_validate(skill, from_attributes=True).model_copy(
        update={"agent_count": int(count or 0)},
    )


@router.patch("/{skill_id}", response_model=SkillRead)
async def update_skill(
    skill_id: UUID,
    payload: SkillUpdate,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> SkillRead:
    """Update a skill in the active organization."""
    skill = await _require_org_skill(session, skill_id=skill_id, ctx=ctx)
    updates = payload.model_dump(exclude_unset=True)

    if "slug" in payload.model_fields_set:
        updates["slug"] = _normalize_slug(
            updates.get("slug"),
            fallback_name=str(updates.get("name") or skill.name),
        )
    if "slug" in updates and isinstance(updates["slug"], str):
        await _ensure_slug_available(
            session,
            organization_id=ctx.organization.id,
            slug=updates["slug"],
            exclude_skill_id=skill.id,
        )
    updates["updated_at"] = utcnow()
    updated = await crud.patch(session, skill, updates)
    return SkillRead.model_validate(updated, from_attributes=True)


@router.delete("/{skill_id}", response_model=OkResponse)
async def delete_skill(
    skill_id: UUID,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> OkResponse:
    """Delete a skill and remove all associated agent-skill links."""
    skill = await _require_org_skill(session, skill_id=skill_id, ctx=ctx)
    await crud.delete_where(
        session,
        AgentSkill,
        col(AgentSkill.skill_id) == skill.id,
        commit=False,
    )
    await session.delete(skill)
    await session.commit()
    return OkResponse()


# ---------------------------------------------------------------------------
# ClawHub proxy endpoints
# ---------------------------------------------------------------------------


@router.get("/clawhub/search", response_model=list[ClawHubSearchResult])
async def search_clawhub(
    q: str,
    limit: int = 20,
    ctx: OrganizationContext = ORG_MEMBER_DEP,
) -> list[ClawHubSearchResult]:
    """Proxy search to the ClawHub registry."""
    results = await clawhub.search_skills(q, limit=min(limit, 50))
    return [
        ClawHubSearchResult(
            slug=r.get("slug"),
            display_name=r.get("displayName"),
            summary=r.get("summary"),
            version=r.get("version"),
            score=r.get("score", 0),
            updated_at=r.get("updatedAt"),
        )
        for r in results
    ]


@router.get("/clawhub/{slug}", response_model=ClawHubSkillDetail)
async def get_clawhub_skill(
    slug: str,
    ctx: OrganizationContext = ORG_MEMBER_DEP,
) -> ClawHubSkillDetail:
    """Fetch a single skill detail from ClawHub."""
    detail = await clawhub.get_skill(slug)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{slug}' not found on ClawHub.",
        )
    skill_data = detail.get("skill", {})
    latest = detail.get("latestVersion") or {}
    owner = detail.get("owner") or {}
    return ClawHubSkillDetail(
        slug=skill_data.get("slug", slug),
        display_name=skill_data.get("displayName", slug),
        summary=skill_data.get("summary"),
        tags=skill_data.get("tags"),
        stats=skill_data.get("stats"),
        latest_version=latest.get("version"),
        latest_changelog=latest.get("changelog"),
        owner_handle=owner.get("handle"),
        owner_display_name=owner.get("displayName"),
    )


@router.post("/clawhub/import", response_model=SkillRead)
async def import_clawhub_skill(
    payload: ClawHubImport,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> SkillRead:
    """Import a skill from ClawHub into the organization's skill directory."""
    slug = slugify_skill(payload.clawhub_slug)
    await _ensure_slug_available(
        session,
        organization_id=ctx.organization.id,
        slug=slug,
    )
    skill = await clawhub.import_skill(
        session,
        organization_id=ctx.organization.id,
        clawhub_slug=payload.clawhub_slug,
        name_override=payload.name,
        category=payload.category,
    )
    return SkillRead.model_validate(skill, from_attributes=True)


@router.post("/{skill_id}/refresh", response_model=SkillRead)
async def refresh_clawhub_skill(
    skill_id: UUID,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> SkillRead:
    """Re-sync a ClawHub-sourced skill with the latest version."""
    skill = await _require_org_skill(session, skill_id=skill_id, ctx=ctx)
    updated = await clawhub.refresh_skill(session, skill)
    return SkillRead.model_validate(updated, from_attributes=True)
