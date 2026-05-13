import asyncio
from sqlmodel import select
from app.db.session import engine
from app.models.user import RefreshToken
from sqlmodel.ext.asyncio.session import AsyncSession
import sys

async def main():
    async with AsyncSession(engine) as db:
        result = await db.exec(select(RefreshToken))
        tokens = result.all()
        print(f"Total tokens in DB: {len(tokens)}")
        for t in tokens:
            print(t.token[:20], t.expires_at, t.revoked)

asyncio.run(main())
