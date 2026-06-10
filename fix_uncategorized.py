import asyncio
import random
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.db.session import engine
from app.models.services import Service, ServiceCategory, ServiceCategoryLink, ServiceStatus, ServiceType
from app.models.user import Users

async def fix_uncategorized():
    async with AsyncSession(engine, expire_on_commit=False) as session:
        # Create or fetch "Other Services" category
        q = select(ServiceCategory).where(ServiceCategory.name == "Other Services")
        result = await session.exec(q)
        other_cat = result.first()
        if not other_cat:
            other_cat = ServiceCategory(name="Other Services", description="Miscellaneous services")
            session.add(other_cat)
            await session.commit()
            await session.refresh(other_cat)

        # Get all services
        q_services = select(Service)
        res = await session.exec(q_services)
        services = res.all()

        linked_service_ids = set()
        q_links = select(ServiceCategoryLink)
        res_links = await session.exec(q_links)
        for link in res_links.all():
            linked_service_ids.add(link.service_id)

        uncategorized = [s for s in services if s.id not in linked_service_ids]

        print(f"Found {len(uncategorized)} uncategorized services.")
        
        for s in uncategorized:
            link = ServiceCategoryLink(service_id=s.id, category_id=other_cat.id)
            session.add(link)
        
        await session.commit()

        # If we have 0 uncategorized, let's create 5 "Other Services" for testing
        if len(uncategorized) == 0:
            print("Creating 5 dummy uncategorized services...")
            q_user = select(Users).where(Users.username == "TestProvider")
            res_user = await session.exec(q_user)
            user = res_user.first()
            
            if user:
                for i in range(5):
                    srv = Service(
                        name=f"Random Miscellaneous Task {i+1}",
                        description="This service doesn't fit into the main categories.",
                        type=ServiceType.online,
                        username=user.username,
                        user_id=user.id,
                        upvotes=random.randint(0, 50),
                        status=ServiceStatus.approved,
                        price=round(random.uniform(5.0, 50.0), 2),
                    )
                    session.add(srv)
                    await session.commit()
                    await session.refresh(srv)

                    link = ServiceCategoryLink(service_id=srv.id, category_id=other_cat.id)
                    session.add(link)
                    await session.commit()
                print("Created 5 dummy Other Services!")
            else:
                print("TestProvider not found, couldn't create dummy services.")

if __name__ == "__main__":
    asyncio.run(fix_uncategorized())
