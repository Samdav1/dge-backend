import pkgutil, importlib
from fastapi import APIRouter

router = APIRouter()

for _, module_name, _ in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f"{__name__}.{module_name}")
    if hasattr(module, "router"):
        router.include_router(module.router, prefix=f"/{module_name}", tags=[module_name])

# Also alias categories router directly at root level
try:
    from app.api.v1.service_category import router as category_router
    router.include_router(category_router, prefix="", tags=["categories"])
except Exception as e:
    pass
