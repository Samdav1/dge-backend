import asyncio
import sys
import os
import uuid

# Ensure the app module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select
from passlib.hash import pbkdf2_sha256 as encrypt
from app.db.session import engine
from app.models.admin import SuperAdmin, AdminRank, AdminStatus

async def create_admin():
    email = "admin@dge.space"
    password = "SuperSecureAdminPassword2026!"
    name = "DGE Administrator"
    
    async with AsyncSession(engine) as session:
        # Check if already exists
        stmt = select(SuperAdmin).where(SuperAdmin.email == email)
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()
        
        if existing:
            print(f"SuperAdmin with email '{email}' already exists.")
            print("Credentials:")
            print(f"  Email: {email}")
            print(f"  Password: {password} (if previously created with this default)")
            return

        new_admin = SuperAdmin(
            id=uuid.uuid4(),
            name=name,
            email=email,
            phone_number="+2348000000000",
            hashed_password=encrypt.encrypt(password),
            rank=AdminRank.Super,
            status=AdminStatus.Approved,
            is_active=True,
            email_verified=True,
            phone_verified=True,
            mfa_enabled=False,
            avatar=""
        )
        session.add(new_admin)
        await session.commit()
        print("SuperAdmin created successfully!")
        print("Credentials:")
        print(f"  Email: {email}")
        print(f"  Password: {password}")

if __name__ == "__main__":
    asyncio.run(create_admin())
