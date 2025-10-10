import uvicorn
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from app.db.session import init_db
from app.websocket_endpoints import router as ws_router
import app.models
from app.api.v1 import router as api_router
from app.core.api_key import get_api_key
from app.dependencies.socket_connection import ConnectionManager
from app.dependencies.call_manager import CallManager


# === Initialize Managers ===
manager = ConnectionManager(redis_url="redis://localhost:6379/0")
call_manager = CallManager(redis_url="redis://localhost:6379/0")


# === Lifespan handles startup & shutdown ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    await manager.start()
    await call_manager.start()
    print("✅ Managers started and Redis connected")

    yield  # App runs during this phase

    # Shutdown logic
    await manager.stop()
    await call_manager.stop()  # <-- FIX: stop() instead of start()
    print("🛑 Managers stopped and Redis closed")


# === App Instance ===
app = FastAPI(
    title="DGE Techs",
    lifespan=lifespan,
)


# === Routers ===
app.include_router(api_router, dependencies=[Depends(get_api_key)])
app.include_router(ws_router)


# === Root Endpoint ===
@app.get("/")
async def root():
    return {"message": "Hello World"}


# === Local Development Entry ===
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
