import asyncio
import uuid
from sqlmodel import select
from app.db.session import engine
from app.models.services import Service, ServiceCategory, ServiceCategoryLink
from app.repositories.services_repo import ServiceRepository
from sqlmodel.ext.asyncio.session import AsyncSession

async def main():
    async with AsyncSession(engine) as db:
        # 1. Fetch a service
        service_q = select(Service)
        result = await db.exec(service_q)
        service = result.first()
        if not service:
            print("No service found in database to test with.")
            return

        print(f"Testing with Service: {service.name} (ID: {service.id})")

        # 2. Fetch all categories
        cat_q = select(ServiceCategory)
        result = await db.exec(cat_q)
        categories = result.all()
        if not categories:
            print("No categories found in database.")
            return

        print(f"Found {len(categories)} categories in DB.")
        for idx, cat in enumerate(categories):
            print(f"  [{idx}] {cat.name} (ID: {cat.id})")

        # Pick the first category to associate with
        target_cat = categories[0]
        print(f"Target category: {target_cat.name} (ID: {target_cat.id})")

        # 3. Instantiate ServiceRepository
        repo = ServiceRepository(db)

        # 4. Try updating
        print("Calling repo.update with target category...")
        updated_service = await repo.update(service, [target_cat.id])
        print("Repo update finished.")

        # 5. Let's verify what is returned
        print(f"Returned service categories: {[c.name for c in updated_service.categories]}")

        # 6. Fetch from db again in a clean session/query to verify persistence
        # (Close the session to clear identity map/cache)
        
    async with AsyncSession(engine) as db2:
        # Re-fetch from db
        from sqlalchemy.orm import selectinload
        q = select(Service).where(Service.id == service.id).options(selectinload(Service.categories))
        result = await db2.exec(q)
        fresh_service = result.first()
        print(f"Freshly queried service categories: {[c.name for c in fresh_service.categories]}")
        
        # Test updating with no categories (empty list)
        print("Updating to empty categories...")
        repo2 = ServiceRepository(db2)
        updated_empty = await repo2.update(fresh_service, [])
        print(f"Returned empty categories: {[c.name for c in updated_empty.categories]}")

    async with AsyncSession(engine) as db3:
        # Re-fetch from db
        from sqlalchemy.orm import selectinload
        q = select(Service).where(Service.id == service.id).options(selectinload(Service.categories))
        result = await db3.exec(q)
        fresh_service = result.first()
        print(f"Freshly queried service categories (should be empty): {[c.name for c in fresh_service.categories]}")

if __name__ == "__main__":
    asyncio.run(main())
