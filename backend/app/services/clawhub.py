"""HTTP client for the ClawHub skill registry API."""

from __future__ import annotations

import io
import zipfile
from typing import Any
from uuid import UUID

import httpx

from app.core.logging import get_logger
from app.core.time import utcnow
from app.db import crud
from app.models.skills import Skill
from app.services.skills import slugify_skill

logger = get_logger(__name__)

CLAWHUB_API_BASE = "https://clawhub.ai/api/v1"
_CLIENT_TIMEOUT = 30.0


def _base_url() -> str:
    """Return the ClawHub registry base URL.

    Can be overridden via settings in the future.
    """
    return CLAWHUB_API_BASE


async def search_skills(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Search ClawHub for skills using vector search.

    Returns a list of search results with score, slug, displayName, summary, etc.
    """
    async with httpx.AsyncClient(timeout=_CLIENT_TIMEOUT) as client:
        response = await client.get(
            f"{_base_url()}/search",
            params={"q": query, "limit": limit},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])


async def list_skills(cursor: str | None = None) -> dict[str, Any]:
    """List skills from ClawHub with cursor-based pagination.

    Returns {items: [...], nextCursor: str | None}.
    """
    params: dict[str, Any] = {}
    if cursor:
        params["cursor"] = cursor
    async with httpx.AsyncClient(timeout=_CLIENT_TIMEOUT) as client:
        response = await client.get(f"{_base_url()}/skills", params=params)
        response.raise_for_status()
        return response.json()


async def get_skill(slug: str) -> dict[str, Any] | None:
    """Fetch a single skill detail from ClawHub by slug.

    Returns {skill, latestVersion, owner} or None if not found.
    """
    async with httpx.AsyncClient(timeout=_CLIENT_TIMEOUT) as client:
        response = await client.get(f"{_base_url()}/skills/{slug}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()


async def download_skill_files(slug: str, tag: str = "latest") -> bytes:
    """Download a skill's files as a zip archive from ClawHub."""
    async with httpx.AsyncClient(timeout=_CLIENT_TIMEOUT) as client:
        response = await client.get(
            f"{_base_url()}/download",
            params={"slug": slug, "tag": tag},
        )
        response.raise_for_status()
        return response.content


def _extract_skill_md(zip_bytes: bytes) -> str | None:
    """Extract SKILL.md content from a skill zip archive.

    Searches for a file named SKILL.md (case-insensitive) in the archive.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for name in zf.namelist():
                basename = name.rsplit("/", 1)[-1] if "/" in name else name
                if basename.upper() == "SKILL.MD":
                    return zf.read(name).decode("utf-8")
    except (zipfile.BadZipFile, KeyError, UnicodeDecodeError):
        logger.warning("clawhub.extract_skill_md.failed slug zip extraction failed")
    return None


async def import_skill(
    session: Any,
    *,
    organization_id: UUID,
    clawhub_slug: str,
    name_override: str | None = None,
    category: str | None = None,
) -> Skill:
    """Fetch a skill from ClawHub and create a local Skill record.

    Downloads the skill metadata and zip, extracts SKILL.md for instructions,
    and persists to the database.
    """
    detail = await get_skill(clawhub_slug)
    if detail is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{clawhub_slug}' not found on ClawHub.",
        )

    skill_data = detail.get("skill", {})
    latest_version = detail.get("latestVersion") or {}
    owner = detail.get("owner") or {}

    display_name = name_override or skill_data.get("displayName", clawhub_slug)
    slug = slugify_skill(clawhub_slug)
    summary = skill_data.get("summary")

    instructions: str | None = None
    try:
        zip_bytes = await download_skill_files(clawhub_slug)
        instructions = _extract_skill_md(zip_bytes)
    except httpx.HTTPError:
        logger.warning(
            "clawhub.import.download_failed slug=%s",
            clawhub_slug,
        )

    clawhub_metadata: dict[str, Any] = {}
    if skill_data.get("stats"):
        clawhub_metadata["stats"] = skill_data["stats"]
    if owner:
        clawhub_metadata["owner"] = {
            "handle": owner.get("handle"),
            "displayName": owner.get("displayName"),
        }
    if skill_data.get("tags"):
        clawhub_metadata["tags"] = skill_data["tags"]

    skill = await crud.create(
        session,
        Skill,
        organization_id=organization_id,
        name=display_name,
        slug=slug,
        summary=summary,
        instructions=instructions,
        source="clawhub",
        clawhub_slug=clawhub_slug,
        clawhub_version=latest_version.get("version"),
        clawhub_metadata=clawhub_metadata or None,
        category=category,
    )
    return skill


async def refresh_skill(
    session: Any,
    skill: Skill,
) -> Skill:
    """Re-sync a ClawHub-sourced skill with the latest version.

    Pulls fresh metadata, downloads the latest zip, and updates the record.
    """
    if not skill.clawhub_slug:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill is not sourced from ClawHub.",
        )

    detail = await get_skill(skill.clawhub_slug)
    if detail is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill.clawhub_slug}' no longer found on ClawHub.",
        )

    skill_data = detail.get("skill", {})
    latest_version = detail.get("latestVersion") or {}
    owner = detail.get("owner") or {}

    try:
        zip_bytes = await download_skill_files(skill.clawhub_slug)
        instructions = _extract_skill_md(zip_bytes)
        if instructions:
            skill.instructions = instructions
    except httpx.HTTPError:
        logger.warning(
            "clawhub.refresh.download_failed slug=%s",
            skill.clawhub_slug,
        )

    skill.summary = skill_data.get("summary") or skill.summary
    skill.clawhub_version = latest_version.get("version")

    clawhub_metadata: dict[str, Any] = {}
    if skill_data.get("stats"):
        clawhub_metadata["stats"] = skill_data["stats"]
    if owner:
        clawhub_metadata["owner"] = {
            "handle": owner.get("handle"),
            "displayName": owner.get("displayName"),
        }
    if skill_data.get("tags"):
        clawhub_metadata["tags"] = skill_data["tags"]
    skill.clawhub_metadata = clawhub_metadata or None

    skill.updated_at = utcnow()
    await crud.save(session, skill)
    return skill
