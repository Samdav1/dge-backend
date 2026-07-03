import asyncio
from sqlmodel import select
from app.db.session import engine
from app.models.services import Service, ServiceCategory, ServiceCategoryLink, ServiceStatus
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

async def main():
    async with AsyncSession(engine) as db:
        # 1. Total services
        q_all = select(Service).options(selectinload(Service.categories))
        res = await db.exec(q_all)
        services = res.all()
        print(f"Total services in DB: {len(services)}")
        for s in services:
            cat_names = [c.name for c in s.categories]
            print(f"  - Service: {s.name} | Status: {s.status} | Price: {s.price} | Categories: {cat_names}")

        # 2. Total categories
        q_cats = select(ServiceCategory)
        res_cats = await db.exec(q_cats)
        categories = res_cats.all()
        print(f"\nTotal categories in DB: {len(categories)}")
        for c in categories:
            print(f"  - Category: {c.name} | ID: {c.id}")

        # 3. Category Links
        q_links = select(ServiceCategoryLink)
        res_links = await db.exec(q_links)
        links = res_links.all()
        print(f"\nTotal category links: {len(links)}")
        for l in links:
            print(f"  - Service ID: {l.service_id} | Category ID: {l.category_id}")

        # 4. Check query from repository
        # This is what list() does:
        # q = select(Service).where(Service.status != ServiceStatus.draft)
        # and then joins/filters
        print("\nSimulating repository list() for marketplace (excluding drafts):")
        q_list = select(Service).where(Service.status != ServiceStatus.draft).options(selectinload(Service.categories))
        res_list = await db.exec(q_list)
        listed = res_list.all()
        print(f"Listed services (non-drafts): {len(listed)}")
        for s in listed:
            print(f"  - {s.name} (Status: {s.status})")

if __name__ == "__main__":
    asyncio.run(main())
