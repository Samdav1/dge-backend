import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from app.db.session import init_db, get_session
from sqlmodel import select
from app.models.driving import DriverProfile

async def check():
    await init_db()
    async for session in get_session():
        res = await session.execute(select(DriverProfile))
        profiles = res.scalars().all()
        print(f"Driver profiles count: {len(profiles)}")
        for p in profiles:
            print(f"Driver ID: {p.id}, License Number: {p.license_number}, License Status: {p.license_status}")
        break

if __name__ == "__main__":
    asyncio.run(check())
