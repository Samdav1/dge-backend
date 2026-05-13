import asyncio
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import engine
from sqlalchemy import text

async def main():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [row[0] for row in result]
        print(f"Tables: {', '.join(tables)}")

asyncio.run(main())
