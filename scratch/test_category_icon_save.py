import asyncio
from sqlmodel import select
from app.db.session import engine
from app.models.services import ServiceCategory
from app.repositories.service_category_repo import ServiceCategoryRepository
from sqlmodel.ext.asyncio.session import AsyncSession

async def main():
    async with AsyncSession(engine) as db:
        repo = ServiceCategoryRepository(db)
        
        # Create a new test category with a unique name
        cat_name = "AI Tester Category 🚀"
        cat_icon = "🤖"
        
        # Check if already exists, clean it up
        stmt = select(ServiceCategory).where(ServiceCategory.name == cat_name)
        result = await db.exec(stmt)
        existing = result.first()
        if existing:
            print(f"Deleting existing test category: {existing.name}")
            await repo.delete_category(existing)
            
        print("Creating test category...")
        new_cat = ServiceCategory(name=cat_name, icon=cat_icon)
        saved_cat = await repo.create_category(new_cat)
        print(f"Saved category: {saved_cat.name}, Icon: {saved_cat.icon}")
        assert saved_cat.icon == cat_icon, "Icon wasn't saved correctly!"
        
        # Now update it
        print("Updating test category icon...")
        saved_cat.icon = "🧠"
        updated_cat = await repo.update_category(saved_cat)
        print(f"Updated category: {updated_cat.name}, Icon: {updated_cat.icon}")
        assert updated_cat.icon == "🧠", "Icon wasn't updated correctly!"
        
        # Clean up
        print("Cleaning up test category...")
        await repo.delete_category(updated_cat)
        print("Test passed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
