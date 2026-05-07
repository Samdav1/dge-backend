import os
import uuid
from fastapi import HTTPException, status, UploadFile, Response
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from passlib.hash import pbkdf2_sha256 as encrypt
from app.models.admin import SuperAdmin
from app.repositories.super_admin_repo import SuperAdminRepository
from app.schemas.super_admin import AdminLogin, SuperAdminRead
from app.core.security import get_access_token, get_refresh_token

AVATAR_DIR = "static/avatars"


class SuperAdminService:
    def __init__(self):
        self.repo = SuperAdminRepository()

    async def create_superadmin(
            self,
            session: AsyncSession,
            name: str,
            email: str,
            password: str,
            phone_number: str | None,
            rank,
            avatar_file: UploadFile | None,
    ) -> SuperAdmin:
        """

        :param session:
        :param name:
        :param email:
        :param password:
        :param phone_number:
        :param rank:
        :param avatar_file:
        :return:
        """
        existing = await self.repo.get_by_email(session, email)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

        if phone_number:
            existing_phone = await self.repo.get_by_phone(session, phone_number)
            if existing_phone:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already exists")

        avatar_path = None
        if avatar_file:
            os.makedirs(AVATAR_DIR, exist_ok=True)
            file_ext = os.path.splitext(avatar_file.filename)[1]
            filename = f"{uuid.uuid4()}{file_ext}"
            avatar_path = os.path.join(AVATAR_DIR, filename)
            with open(avatar_path, "wb") as f:
                f.write(await avatar_file.read())

        new_admin = SuperAdmin(
            name=name,
            email=email,
            phone_number=phone_number,
            hashed_password=encrypt.encrypt(password),
            rank=rank,
            avatar=avatar_path or "",
        )

        try:
            await self.repo.add(session, new_admin)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict while creating SuperAdmin")
        except Exception:
            await session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")

        await session.refresh(new_admin)
        return new_admin

    async def list_superadmins(self, session: AsyncSession):
        return await self.repo.list_all(session)

    async def get_superadmin(self, session: AsyncSession, admin_id: uuid.UUID):
        admin = await self.repo.get_by_id(session, admin_id)
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SuperAdmin not found")
        return admin

    async def delete_superadmin(self, session: AsyncSession, admin_id: uuid.UUID):
        admin = await self.get_superadmin(session, admin_id)
        await self.repo.delete(session, admin)
        await session.commit()
        return {"message": "SuperAdmin deleted successfully"}

    async def admin_login(self, session: AsyncSession, admin_info: AdminLogin):
        admin = await self.repo.get_by_email(session, admin_info.username)
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SuperAdmin not found")

        if not encrypt.verify(admin_info.password, admin.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
        refined_admin = SuperAdminRead.model_validate(admin)
        return refined_admin