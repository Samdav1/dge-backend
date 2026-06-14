import asyncio
from sqlmodel import select
from app.db.session import engine
from app.models.user import RefreshToken
from sqlmodel.ext.asyncio.session import AsyncSession

async def main():
    async with AsyncSession(engine) as db:
        result = await db.exec(select(RefreshToken).where(RefreshToken.user_id == "5a26c322-237e-4538-af48-d1cc7ea1748c"))
        tokens = result.all()
        print(f"Total tokens for user: {len(tokens)}")
        for t in tokens:
            print(t.token[:20], t.expires_at, t.revoked)

if __name__ == "__main__":
    asyncio.run(main())
