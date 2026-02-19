"""Board file attachment CRUD endpoints."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlmodel import col

from app.api.deps import (
    ActorContext,
    get_board_for_actor_read,
    get_board_for_actor_write,
    require_admin_or_agent,
)
from app.core.config import settings
from app.db.pagination import paginate
from app.db.session import get_session
from app.models.board_attachments import BoardAttachment
from app.schemas.board_attachments import BoardAttachmentRead
from app.schemas.common import OkResponse
from app.schemas.pagination import DefaultLimitOffsetPage

if TYPE_CHECKING:
    from fastapi_pagination.limit_offset import LimitOffsetPage
    from sqlmodel.ext.asyncio.session import AsyncSession

    from app.models.boards import Board

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/boards/{board_id}/attachments", tags=["board-attachments"])

BOARD_READ_DEP = Depends(get_board_for_actor_read)
BOARD_WRITE_DEP = Depends(get_board_for_actor_write)
SESSION_DEP = Depends(get_session)
ACTOR_DEP = Depends(require_admin_or_agent)
_RUNTIME_TYPE_REFERENCES = (UUID,)


def _base_url() -> str:
    return (settings.base_url or "http://localhost:8000").rstrip("/")


def _to_read(attachment: BoardAttachment) -> BoardAttachmentRead:
    return BoardAttachmentRead(
        id=attachment.id,
        board_id=attachment.board_id,
        filename=attachment.filename,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        uploaded_by=attachment.uploaded_by,
        description=attachment.description,
        download_url=(
            f"{_base_url()}/api/v1/boards/{attachment.board_id}"
            f"/attachments/{attachment.id}/download"
        ),
        created_at=attachment.created_at,
    )


def _uploads_root() -> Path:
    return Path(settings.uploads_root)


def _actor_display(actor: ActorContext) -> str:
    if actor.actor_type == "agent" and actor.agent:
        return f"agent:{actor.agent.name}"
    if actor.user:
        return f"user:{actor.user.preferred_name or actor.user.name or 'User'}"
    return "user:User"


@router.get("", response_model=DefaultLimitOffsetPage[BoardAttachmentRead])
async def list_board_attachments(
    *,
    board: Board = BOARD_READ_DEP,
    session: AsyncSession = SESSION_DEP,
    _actor: ActorContext = ACTOR_DEP,
) -> LimitOffsetPage[BoardAttachmentRead]:
    """List file attachments for a board."""
    statement = BoardAttachment.objects.filter_by(board_id=board.id).order_by(
        col(BoardAttachment.created_at).desc(),
    )
    return await paginate(
        session,
        statement.statement,
        transformer=lambda items: [_to_read(item) for item in items],
    )


@router.post("", response_model=BoardAttachmentRead, status_code=201)
async def upload_board_attachment(
    file: UploadFile,
    board: Board = BOARD_WRITE_DEP,
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
    description: str | None = Form(default=None),
) -> BoardAttachmentRead:
    """Upload a file attachment to a board."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    # Read file content with size check
    max_size = settings.max_upload_size_bytes
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum size of {max_size // (1024 * 1024)} MB.",
            )
        chunks.append(chunk)

    if total == 0:
        raise HTTPException(status_code=400, detail="Empty file.")

    # Check board total
    current_total = (
        await session.exec(
            BoardAttachment.objects.filter_by(board_id=board.id)
            .statement.with_only_columns(func.coalesce(func.sum(col(BoardAttachment.size_bytes)), 0))
        )
    ).one()
    max_board = settings.max_board_attachments_bytes
    if int(current_total) + total > max_board:
        raise HTTPException(
            status_code=413,
            detail=f"Board attachment storage limit ({max_board // (1024 * 1024)} MB) would be exceeded.",
        )

    attachment_id = uuid4()
    content_type = file.content_type or "application/octet-stream"
    storage_path = f"{board.id}/{attachment_id}/{file.filename}"
    file_path = _uploads_root() / storage_path

    # Write file to disk
    file_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(file_path, "wb") as f:
            for chunk in chunks:
                f.write(chunk)
    except OSError as exc:
        logger.error("board_attachment.write_failed path=%s error=%s", file_path, exc)
        raise HTTPException(status_code=500, detail="Failed to store file.") from exc

    # Create DB row
    attachment = BoardAttachment(
        id=attachment_id,
        board_id=board.id,
        filename=file.filename,
        content_type=content_type,
        size_bytes=total,
        storage_path=storage_path,
        uploaded_by=_actor_display(actor),
        description=description,
    )
    session.add(attachment)
    try:
        await session.commit()
        await session.refresh(attachment)
    except Exception:
        # Clean up file on DB failure
        file_path.unlink(missing_ok=True)
        try:
            file_path.parent.rmdir()
        except OSError:
            pass
        raise

    return _to_read(attachment)


@router.get("/{attachment_id}", response_model=BoardAttachmentRead)
async def get_board_attachment(
    attachment_id: UUID,
    board: Board = BOARD_READ_DEP,
    session: AsyncSession = SESSION_DEP,
    _actor: ActorContext = ACTOR_DEP,
) -> BoardAttachmentRead:
    """Get metadata for a single attachment."""
    attachment = await BoardAttachment.objects.filter_by(
        id=attachment_id,
        board_id=board.id,
    ).first(session)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found.")
    return _to_read(attachment)


@router.get("/{attachment_id}/download")
async def download_board_attachment(
    attachment_id: UUID,
    board: Board = BOARD_READ_DEP,
    session: AsyncSession = SESSION_DEP,
    _actor: ActorContext = ACTOR_DEP,
) -> FileResponse:
    """Download the file for an attachment."""
    attachment = await BoardAttachment.objects.filter_by(
        id=attachment_id,
        board_id=board.id,
    ).first(session)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found.")

    file_path = _uploads_root() / attachment.storage_path
    if not file_path.is_file():
        logger.error("board_attachment.file_missing path=%s", file_path)
        raise HTTPException(status_code=404, detail="File not found on disk.")

    return FileResponse(
        path=str(file_path),
        media_type=attachment.content_type,
        filename=attachment.filename,
    )


@router.delete("/{attachment_id}", response_model=OkResponse)
async def delete_board_attachment(
    attachment_id: UUID,
    board: Board = BOARD_WRITE_DEP,
    session: AsyncSession = SESSION_DEP,
    _actor: ActorContext = ACTOR_DEP,
) -> OkResponse:
    """Delete an attachment and its file from disk."""
    attachment = await BoardAttachment.objects.filter_by(
        id=attachment_id,
        board_id=board.id,
    ).first(session)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found.")

    # Delete file from disk
    file_path = _uploads_root() / attachment.storage_path
    if file_path.is_file():
        file_path.unlink(missing_ok=True)
        try:
            file_path.parent.rmdir()
        except OSError:
            pass

    await session.delete(attachment)
    await session.commit()
    return OkResponse()


async def delete_board_attachments(session: AsyncSession, board_id: UUID) -> None:
    """Delete all attachments for a board (used during board deletion)."""
    attachments = await BoardAttachment.objects.filter_by(board_id=board_id).all(session)
    for attachment in attachments:
        file_path = _uploads_root() / attachment.storage_path
        if file_path.is_file():
            file_path.unlink(missing_ok=True)
            try:
                file_path.parent.rmdir()
            except OSError:
                pass
        await session.delete(attachment)

    # Remove the board's upload directory
    board_dir = _uploads_root() / str(board_id)
    if board_dir.is_dir():
        shutil.rmtree(board_dir, ignore_errors=True)
