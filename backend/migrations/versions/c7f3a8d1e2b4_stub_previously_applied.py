"""stub: previously applied migration (file was lost)

Revision ID: c7f3a8d1e2b4
Revises: b5e2d7f8a3c1
Create Date: 2026-02-14 00:00:00.000000

"""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "c7f3a8d1e2b4"
down_revision = "b5e2d7f8a3c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration was previously applied on the production database.
    # The original migration file was lost. This stub exists solely to
    # maintain a valid Alembic revision chain.
    pass


def downgrade() -> None:
    pass
