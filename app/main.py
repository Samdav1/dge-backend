import uvicorn
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.db.session import init_db
from app.websocket_endpoints import router as ws_router
import app.models
from app.api.v1 import router as api_router
from app.core.api_key import get_api_key
from app.dependencies.socket_connection import ConnectionManager, manager
from app.middlewares.auth_middleware import AuthMiddleware
from dotenv import load_dotenv

import os
import asyncio
import logging

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_file_path = os.path.join(base_dir, "server.log")
file_handler = logging.FileHandler(log_file_path, mode="a")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)
# Set appropriate levels
root_logger.setLevel(logging.INFO)
logging.getLogger("app.services.matching_service").setLevel(logging.DEBUG)
logging.getLogger("app.dependencies.socket_connection").setLevel(logging.DEBUG)
logging.getLogger("app.websocket_endpoints.chat_ws").setLevel(logging.DEBUG)
logging.getLogger("app.websocket_endpoints.ride_ws").setLevel(logging.DEBUG)
logging.getLogger("app.api.v1.drivers").setLevel(logging.DEBUG)

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    await manager.start()
    print("✅ Managers started and Redis connected")

    # Run seeding and superadmin in background (non-blocking)
    # so uvicorn can bind to port 8000 immediately for health checks
    async def _background_setup():
        try:
            from seed_categories import seed
            await seed()
            print("✅ Categories seeded")
        except Exception as e:
            print(f"⚠️  Seeding failed (non-fatal): {e}")
        try:
            from add_superadmin import add_admin
            await add_admin()
            print("✅ Superadmin ensured")
        except Exception as e:
            print(f"⚠️  Superadmin insert failed (non-fatal): {e}")

    asyncio.create_task(_background_setup())

    yield

    await manager.stop()
    print("🛑 Managers stopped and Redis closed")


app = FastAPI(
    title="DGE Techs",
    lifespan=lifespan,
)

app.add_middleware(AuthMiddleware)

app.mount("/static", StaticFiles(directory="uploaded_files"), name="static")

app.include_router(api_router, dependencies=[Depends(get_api_key)])
app.include_router(api_router, prefix="/v1", dependencies=[Depends(get_api_key)])
app.include_router(api_router, prefix="/super_admin", dependencies=[Depends(get_api_key)])
app.include_router(ws_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Running on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
