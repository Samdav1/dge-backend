import asyncio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import engine
from app.models.services import Service
from fastapi.encoders import jsonable_encoder

async def test_get():
    async with AsyncSession(engine) as session:
        # Get one service with categories
        from sqlalchemy.orm import selectinload
        q = select(Service).limit(1).options(selectinload(Service.categories))
        res = await session.exec(q)
        service = res.first()
        if not service:
            print("No services found in database")
            return
        
        print("Raw service categories:", service.categories)
        print("jsonable_encoder output for service:")
        import pprint
        pprint.pprint(jsonable_encoder(service))

if __name__ == "__main__":
    asyncio.run(test_get())
