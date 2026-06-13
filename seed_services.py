import asyncio
import random
import uuid
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.db.session import engine
from app.models.user import Users
from app.models.services import Service, ServiceCategory, ServiceCategoryLink, ServiceStatus, ServiceType

async def seed_data():
    async with AsyncSession(engine, expire_on_commit=False) as session:
        # Create a test user
        user = Users(
            username="TestProvider",
            email="provider@example.com",
            password="hashed_password",
            email_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Ensure we have categories
        category_names = ["Web Development", "Plumbing", "Graphic Design", "Writing", "Consulting"]
        categories = []
        for name in category_names:
            q = select(ServiceCategory).where(ServiceCategory.name == name)
            result = await session.exec(q)
            cat = result.first()
            if not cat:
                cat = ServiceCategory(name=name, description=f"{name} services")
                session.add(cat)
                await session.commit()
                await session.refresh(cat)
            categories.append(cat)

        # Generate 50 services
        service_types = [ServiceType.online, ServiceType.physical, ServiceType.hybrid]
        adjectives = ["Professional", "Quick", "Expert", "Reliable", "Affordable", "Premium", "Elite"]

        print("Generating 50 services...")
        for i in range(50):
            cat = random.choice(categories)
            stype = random.choice(service_types)
            adj = random.choice(adjectives)
            
            price = round(random.uniform(10.0, 500.0), 2)
            upvotes = random.randint(0, 1000)
            
            srv = Service(
                name=f"{adj} {cat.name} Service {i+1}",
                description=f"This is a dummy service description for {cat.name}. We provide excellent {stype.value} service.",
                type=stype,
                username=user.username,
                user_id=user.id,
                upvotes=upvotes,
                status=ServiceStatus.approved,
                price=price,
                discount=random.choice([True, False]),
                discount_percent=round(random.uniform(5.0, 20.0), 2) if random.choice([True, False]) else 0.0,
            )
            session.add(srv)
            await session.commit()
            await session.refresh(srv)

            # Link category
            link = ServiceCategoryLink(service_id=srv.id, category_id=cat.id)
            session.add(link)
            await session.commit()

        print("Successfully generated 50 services!")

if __name__ == "__main__":
    asyncio.run(seed_data())
