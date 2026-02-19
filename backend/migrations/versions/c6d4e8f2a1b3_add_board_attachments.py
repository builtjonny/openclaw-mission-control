"""add board_attachments

Revision ID: c6d4e8f2a1b3
Revises: b5e2d7f8a3c1
Create Date: 2026-02-19 12:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c6d4e8f2a1b3"
down_revision = "b5e2d7f8a3c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("board_attachments"):
        op.create_table(
            "board_attachments",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("board_id", sa.Uuid(), nullable=False),
            sa.Column("filename", sa.String(), nullable=False),
            sa.Column("content_type", sa.String(), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("storage_path", sa.String(), nullable=False),
            sa.Column("uploaded_by", sa.String(), nullable=True),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["board_id"], ["boards.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    indexes = {
        item.get("name") for item in inspector.get_indexes("board_attachments")
    }
    if op.f("ix_board_attachments_board_id") not in indexes:
        op.create_index(
            op.f("ix_board_attachments_board_id"),
            "board_attachments",
            ["board_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_board_attachments_board_id"), table_name="board_attachments"
    )
    op.drop_table("board_attachments")
