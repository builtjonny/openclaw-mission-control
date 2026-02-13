"""Add password_hash to users.

Revision ID: a7b3c9d2e5f1
Revises: fa6e83f8d9a1
Create Date: 2026-02-12 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a7b3c9d2e5f1"
down_revision = "fa6e83f8d9a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "password_hash")
