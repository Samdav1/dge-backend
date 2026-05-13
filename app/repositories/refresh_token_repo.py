
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from datetime import datetime, timezone
from app.models.user import RefreshToken


async def create(db: AsyncSession, refresh_token: RefreshToken):
    db.add(refresh_token)
    await db.commit()
    await db.refresh(refresh_token)
    return refresh_token

async def get_by_token(db: AsyncSession, token: str):
    result = await db.exec(select(RefreshToken).where(RefreshToken.token == token))
    return result.first()

async def revoke(db: AsyncSession, token: str):
    db_token = await get_by_token(db, token)
    if db_token:
        db_token.revoked = True
        db_token.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(db_token)
    return db_token

async def delete_expired(db: AsyncSession):
    result = await db.exec(
        select(RefreshToken).where(
            (RefreshToken.revoked == True) |
            (RefreshToken.expires_at < datetime.now(timezone.utc)())
        )
    )
    expired_tokens = result.scalars().all()
    for token in expired_tokens:
        await db.delete(token)
    await db.commit()
    return len(expired_tokens)