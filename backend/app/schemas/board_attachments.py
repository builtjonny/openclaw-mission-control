"""Schemas for board file attachment API payloads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import SQLModel

RUNTIME_ANNOTATION_TYPES = (datetime, UUID)


class BoardAttachmentRead(SQLModel):
    """Serialized board attachment returned from read endpoints."""

    id: UUID
    board_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by: str | None = None
    description: str | None = None
    download_url: str
    created_at: datetime
