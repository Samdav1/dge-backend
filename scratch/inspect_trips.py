import asyncio
from app.db.session import get_session
from sqlalchemy import text

async def main():
    async for session in get_session():
        db = session
        break
    
    res = await db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'trips'"))
    cols = res.fetchall()
    print("Trips columns:")
    for col in cols:
        print(f"- {col[0]} ({col[1]})")

if __name__ == "__main__":
    asyncio.run(main())
