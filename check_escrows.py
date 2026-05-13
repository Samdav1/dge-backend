import asyncio
from sqlmodel import select
from app.db.database import async_session_maker
from app.models.escrow import Escrow

async def main():
    async with async_session_maker() as session:
        result = await session.execute(select(Escrow).order_by(Escrow.created_at.desc()).limit(5))
        escrows = result.scalars().all()
        for e in escrows:
            print(f"ID: {e.id}, Status: {e.status}")

asyncio.run(main())
