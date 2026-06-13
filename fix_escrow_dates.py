import asyncio
from app.db.session import get_session
from app.models.escrow import Escrow
from sqlmodel import select
from datetime import datetime, timezone

async def update():
    async for session in get_session():
        res = await session.execute(select(Escrow).where(Escrow.created_at == None))
        escrows = res.scalars().all()
        for e in escrows:
            now = datetime.now(timezone.utc)
            e.created_at = now
            if not e.updated_at:
                e.updated_at = now
            session.add(e)
        await session.commit()
        print(f"Updated {len(escrows)} escrows")
        break

if __name__ == "__main__":
    asyncio.run(update())
