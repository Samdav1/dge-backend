import asyncio
from app.db.session import get_session
from app.models.escrow import Escrow
from sqlmodel import select

async def check():
    async for session in get_session():
        res = await session.execute(select(Escrow).limit(5))
        escrows = res.scalars().all()
        for e in escrows:
            print(f"ID: {e.id}, Created: {e.created_at}, Updated: {e.updated_at}")
        break

if __name__ == "__main__":
    asyncio.run(check())
