import asyncio
from sqlmodel import select
from app.db.session import engine
from app.models.services import ServiceCategory
from sqlmodel.ext.asyncio.session import AsyncSession

async def main():
    async with AsyncSession(engine) as db:
        stmt = select(ServiceCategory)
        res = await db.exec(stmt)
        categories = res.all()
        print(f"Total categories: {len(categories)}")
        for cat in categories[:10]:
            print(f"ID: {cat.id}, Name: {cat.name}, Icon: {cat.icon}")

if __name__ == "__main__":
    asyncio.run(main())
