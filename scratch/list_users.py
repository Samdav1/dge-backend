import asyncio
from sqlmodel import select
from app.db.session import get_session, init_db
from app.models.user import Users

async def list_users():
    await init_db()
    async for session in get_session():
        statement = select(Users)
        result = await session.execute(statement)
        users = result.scalars().all()
        for u in users:
            print(f"User ID: {u.id}, Username: {u.username}, Email: {u.email}")

asyncio.run(list_users())
