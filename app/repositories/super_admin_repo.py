# app/db/repository/superadmin_repo.py
from typing import Optional, List
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select
from app.models.admin import SuperAdmin


class SuperAdminRepository:
    """Handles direct DB operations (no commits)."""

    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[SuperAdmin]:
        stmt = select(SuperAdmin).where(SuperAdmin.email == email)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_id(self, session: AsyncSession, admin_id: UUID) -> Optional[SuperAdmin]:
        stmt = select(SuperAdmin).where(SuperAdmin.id == admin_id)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all(self, session: AsyncSession) -> List[SuperAdmin]:
        stmt = select(SuperAdmin)
        res = await session.execute(stmt)
        return res.scalars().all()

    async def add(self, session: AsyncSession, admin: SuperAdmin) -> SuperAdmin:
        session.add(admin)
        await session.flush()
        return admin

    async def delete(self, session: AsyncSession, admin: SuperAdmin) -> None:
        await session.delete(admin)
        await session.flush()
