"""add skills and agent_skills

Revision ID: b5e2d7f8a3c1
Revises: a7b3c9d2e5f1
Create Date: 2026-02-13 12:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b5e2d7f8a3c1"
down_revision = "a7b3c9d2e5f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("skills"):
        op.create_table(
            "skills",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("organization_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("slug", sa.String(), nullable=False),
            sa.Column("summary", sa.String(), nullable=True),
            sa.Column("instructions", sa.Text(), nullable=True),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("clawhub_slug", sa.String(), nullable=True),
            sa.Column("clawhub_version", sa.String(), nullable=True),
            sa.Column("clawhub_metadata", sa.JSON(), nullable=True),
            sa.Column("category", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "organization_id",
                "slug",
                name="uq_skills_organization_id_slug",
            ),
        )
    skill_indexes = {item.get("name") for item in inspector.get_indexes("skills")}
    if op.f("ix_skills_organization_id") not in skill_indexes:
        op.create_index(
            op.f("ix_skills_organization_id"),
            "skills",
            ["organization_id"],
            unique=False,
        )
    if op.f("ix_skills_slug") not in skill_indexes:
        op.create_index(
            op.f("ix_skills_slug"),
            "skills",
            ["slug"],
            unique=False,
        )
    if op.f("ix_skills_clawhub_slug") not in skill_indexes:
        op.create_index(
            op.f("ix_skills_clawhub_slug"),
            "skills",
            ["clawhub_slug"],
            unique=False,
        )

    if not inspector.has_table("agent_skills"):
        op.create_table(
            "agent_skills",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("agent_id", sa.Uuid(), nullable=False),
            sa.Column("skill_id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
            sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "agent_id",
                "skill_id",
                name="uq_agent_skills_agent_id_skill_id",
            ),
        )
    agent_skill_indexes = {
        item.get("name") for item in inspector.get_indexes("agent_skills")
    }
    if op.f("ix_agent_skills_agent_id") not in agent_skill_indexes:
        op.create_index(
            op.f("ix_agent_skills_agent_id"),
            "agent_skills",
            ["agent_id"],
            unique=False,
        )
    if op.f("ix_agent_skills_skill_id") not in agent_skill_indexes:
        op.create_index(
            op.f("ix_agent_skills_skill_id"),
            "agent_skills",
            ["skill_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_skills_skill_id"), table_name="agent_skills")
    op.drop_index(op.f("ix_agent_skills_agent_id"), table_name="agent_skills")
    op.drop_table("agent_skills")
    op.drop_index(op.f("ix_skills_clawhub_slug"), table_name="skills")
    op.drop_index(op.f("ix_skills_slug"), table_name="skills")
    op.drop_index(op.f("ix_skills_organization_id"), table_name="skills")
    op.drop_table("skills")
