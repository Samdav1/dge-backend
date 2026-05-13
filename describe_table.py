import asyncio
from app.db.session import engine
from sqlalchemy import text

async def main():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'posted_jobs'"))
        columns = [f"{row[0]} ({row[1]})" for row in result]
        print(f"posted_jobs columns: {', '.join(columns)}")

asyncio.run(main())
