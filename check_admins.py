import asyncio
from app.db.session import init_db, get_session
from sqlmodel import select
from app.models.admin import SuperAdmin

async def check():
    await init_db()
    async for session in get_session():
        res = await session.execute(select(SuperAdmin))
        admins = res.scalars().all()
        print(f"Admins count: {len(admins)}")
        for a in admins:
            print(f"Admin: {a.name}, Email: {a.email}, Status: {a.status}")
        break

if __name__ == "__main__":
    asyncio.run(check())
