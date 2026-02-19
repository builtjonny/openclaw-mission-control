"""Thin API wrappers for async agent lifecycle operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import SQLModel
from sse_starlette.sse import EventSourceResponse

from app.api.deps import ActorContext, require_admin_or_agent, require_org_admin
from app.core.auth import AuthContext, get_auth_context
from app.core.time import utcnow
from app.db.session import get_session
from app.models.agents import Agent
from app.models.gateways import Gateway
from app.schemas.agents import (
    AgentCreate,
    AgentHeartbeat,
    AgentHeartbeatCreate,
    AgentRead,
    AgentUpdate,
)
from app.schemas.common import OkResponse
from app.schemas.pagination import DefaultLimitOffsetPage
from app.services.openclaw.gateway_resolver import gateway_client_config
from app.services.openclaw.gateway_rpc import OpenClawGatewayError, openclaw_call
from app.services.openclaw.internal.agent_key import agent_key
from app.services.openclaw.provisioning_db import AgentLifecycleService, AgentUpdateOptions
from app.services.organizations import OrganizationContext

if TYPE_CHECKING:
    from fastapi_pagination.limit_offset import LimitOffsetPage
    from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger(__name__)

_EDITABLE_FILES = frozenset({"SOUL.md", "SELF.md", "TASK_SOUL.md"})

router = APIRouter(prefix="/agents", tags=["agents"])

BOARD_ID_QUERY = Query(default=None)
GATEWAY_ID_QUERY = Query(default=None)
SINCE_QUERY = Query(default=None)
SESSION_DEP = Depends(get_session)
ORG_ADMIN_DEP = Depends(require_org_admin)
ACTOR_DEP = Depends(require_admin_or_agent)
AUTH_DEP = Depends(get_auth_context)


@dataclass(frozen=True, slots=True)
class _AgentUpdateParams:
    force: bool
    auth: AuthContext
    ctx: OrganizationContext


def _agent_update_params(
    *,
    force: bool = False,
    auth: AuthContext = AUTH_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> _AgentUpdateParams:
    return _AgentUpdateParams(force=force, auth=auth, ctx=ctx)


AGENT_UPDATE_PARAMS_DEP = Depends(_agent_update_params)


@router.get("", response_model=DefaultLimitOffsetPage[AgentRead])
async def list_agents(
    board_id: UUID | None = BOARD_ID_QUERY,
    gateway_id: UUID | None = GATEWAY_ID_QUERY,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> LimitOffsetPage[AgentRead]:
    """List agents visible to the active organization admin."""
    service = AgentLifecycleService(session)
    return await service.list_agents(
        board_id=board_id,
        gateway_id=gateway_id,
        ctx=ctx,
    )


@router.get("/stream")
async def stream_agents(
    request: Request,
    board_id: UUID | None = BOARD_ID_QUERY,
    since: str | None = SINCE_QUERY,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> EventSourceResponse:
    """Stream agent updates as SSE events."""
    service = AgentLifecycleService(session)
    return await service.stream_agents(
        request=request,
        board_id=board_id,
        since=since,
        ctx=ctx,
    )


@router.post("", response_model=AgentRead)
async def create_agent(
    payload: AgentCreate,
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
) -> AgentRead:
    """Create and provision an agent."""
    service = AgentLifecycleService(session)
    return await service.create_agent(payload=payload, actor=actor)


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(
    agent_id: str,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> AgentRead:
    """Get a single agent by id."""
    service = AgentLifecycleService(session)
    return await service.get_agent(agent_id=agent_id, ctx=ctx)


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    params: _AgentUpdateParams = AGENT_UPDATE_PARAMS_DEP,
    session: AsyncSession = SESSION_DEP,
) -> AgentRead:
    """Update agent metadata and optionally reprovision."""
    service = AgentLifecycleService(session)
    return await service.update_agent(
        agent_id=agent_id,
        payload=payload,
        options=AgentUpdateOptions(
            force=params.force,
            user=params.auth.user,
            context=params.ctx,
        ),
    )


@router.post("/{agent_id}/heartbeat", response_model=AgentRead)
async def heartbeat_agent(
    agent_id: str,
    payload: AgentHeartbeat,
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
) -> AgentRead:
    """Record a heartbeat for a specific agent."""
    service = AgentLifecycleService(session)
    return await service.heartbeat_agent(agent_id=agent_id, payload=payload, actor=actor)


@router.post("/heartbeat", response_model=AgentRead)
async def heartbeat_or_create_agent(
    payload: AgentHeartbeatCreate,
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
) -> AgentRead:
    """Heartbeat an existing agent or create/provision one if needed."""
    service = AgentLifecycleService(session)
    return await service.heartbeat_or_create_agent(payload=payload, actor=actor)


@router.delete("/{agent_id}", response_model=OkResponse)
async def delete_agent(
    agent_id: str,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> OkResponse:
    """Delete an agent and clean related task state."""
    service = AgentLifecycleService(session)
    return await service.delete_agent(agent_id=agent_id, ctx=ctx)


# ---------------------------------------------------------------------------
# Agent workspace file read/write
# ---------------------------------------------------------------------------


def _extract_file_content(payload: object) -> str | None:
    """Extract string content from a gateway agents.files.get response."""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        content = payload.get("content")
        if isinstance(content, str):
            return content
        file_obj = payload.get("file")
        if isinstance(file_obj, dict):
            nested = file_obj.get("content")
            if isinstance(nested, str):
                return nested
    return None


async def _resolve_agent_and_gateway(
    session: AsyncSession,
    agent_id: str,
) -> tuple[Agent, Gateway]:
    agent = await Agent.objects.by_id(agent_id).first(session)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    gateway = await session.get(Gateway, agent.gateway_id)
    if gateway is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Agent gateway not found",
        )
    return agent, gateway


class _FileContentPayload(SQLModel):
    content: str


@router.get("/{agent_id}/files/{filename}", response_model=str)
async def get_agent_file(
    agent_id: str,
    filename: str,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> str:
    """Read an agent workspace file from the gateway."""
    if filename not in _EDITABLE_FILES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File not editable. Allowed: {', '.join(sorted(_EDITABLE_FILES))}",
        )
    agent, gateway = await _resolve_agent_and_gateway(session, agent_id)
    config = gateway_client_config(gateway)
    try:
        payload = await openclaw_call(
            "agents.files.get",
            {"agentId": agent_key(agent), "name": filename},
            config=config,
        )
    except OpenClawGatewayError as exc:
        logger.error("agents.files.get failed agent_id=%s file=%s error=%s", agent_id, filename, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    content = _extract_file_content(payload)
    if content is None:
        return ""
    return content


@router.put("/{agent_id}/files/{filename}", response_model=OkResponse)
async def update_agent_file(
    agent_id: str,
    filename: str,
    payload: _FileContentPayload,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_ADMIN_DEP,
) -> OkResponse:
    """Write an agent workspace file to the gateway."""
    if filename not in _EDITABLE_FILES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File not editable. Allowed: {', '.join(sorted(_EDITABLE_FILES))}",
        )
    agent, gateway = await _resolve_agent_and_gateway(session, agent_id)
    normalized = payload.content.strip()
    config = gateway_client_config(gateway)
    try:
        await openclaw_call(
            "agents.files.set",
            {"agentId": agent_key(agent), "name": filename, "content": normalized},
            config=config,
        )
    except OpenClawGatewayError as exc:
        logger.error("agents.files.set failed agent_id=%s file=%s error=%s", agent_id, filename, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    # Persist SOUL.md changes in DB so they survive reprovisioning.
    if filename == "SOUL.md":
        agent.soul_template = normalized or None
        agent.updated_at = utcnow()
        session.add(agent)
        await session.commit()
    return OkResponse()
