"""Seed an initial admin user with email/password credentials.

Usage (inside backend container):
    python -m scripts.seed_admin
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging import get_logger
from app.core.passwords import hash_password
from app.core.time import utcnow
from app.db.session import async_session_maker
from app.models.organization_members import OrganizationMember
from app.models.organizations import Organization
from app.models.users import User

logger = get_logger(__name__)

ADMIN_EMAIL = "jonny@builtmighty.com"
ADMIN_PASSWORD = "mJccJ74!"
ADMIN_NAME = "Jonny"
ORG_NAME = "Built Mighty"


async def seed(session: AsyncSession) -> None:
    # Check if user already exists.
    existing = (
        await session.exec(
            select(User).where(func.lower(col(User.email)) == ADMIN_EMAIL.lower())
        )
    ).first()
    if existing is not None:
        # Update password hash if user exists but has no password.
        if not existing.password_hash:
            existing.password_hash = hash_password(ADMIN_PASSWORD)
            existing.is_super_admin = True
            session.add(existing)
            await session.commit()
            logger.info("Updated existing user with password hash: %s", ADMIN_EMAIL)
        else:
            logger.info("Admin user already exists: %s", ADMIN_EMAIL)
        return

    local_user_id = f"local-{uuid4()}"
    user = User(
        clerk_user_id=local_user_id,
        email=ADMIN_EMAIL,
        name=ADMIN_NAME,
        password_hash=hash_password(ADMIN_PASSWORD),
        is_super_admin=True,
    )
    session.add(user)
    await session.flush()

    now = utcnow()

    # Create or find an organization.
    org = (
        await session.exec(
            select(Organization).where(
                func.lower(col(Organization.name)) == ORG_NAME.lower()
            )
        )
    ).first()
    if org is None:
        org = Organization(name=ORG_NAME, created_at=now, updated_at=now)
        session.add(org)
        await session.flush()
        logger.info("Created organization: %s", ORG_NAME)

    # Create membership as owner.
    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role="owner",
        all_boards_read=True,
        all_boards_write=True,
        created_at=now,
        updated_at=now,
    )
    session.add(member)

    user.active_organization_id = org.id
    session.add(user)

    await session.commit()
    logger.info("Seeded admin user: %s (super_admin=True, org=%s)", ADMIN_EMAIL, ORG_NAME)


async def main() -> None:
    async with async_session_maker() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
