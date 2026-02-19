"""Board file attachment metadata model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel

RUNTIME_ANNOTATION_TYPES = (datetime,)


class BoardAttachment(QueryModel, table=True):
    """File attachment linked to a board."""

    __tablename__ = "board_attachments"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    board_id: UUID = Field(foreign_key="boards.id", index=True)
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    uploaded_by: str | None = None
    description: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
