import asyncio
from app.db.session import init_db

async def main():
    print("Running init_db()...")
    await init_db()
    print("Migrations complete!")

if __name__ == "__main__":
    asyncio.run(main())
