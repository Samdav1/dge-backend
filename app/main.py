import uvicorn
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.db.session import init_db
from app.websocket_endpoints import router as ws_router
import app.models
from app.api.v1 import router as api_router
from app.core.api_key import get_api_key
from app.dependencies.socket_connection import ConnectionManager
from app.middlewares.auth_middleware import AuthMiddleware


manager = ConnectionManager(redis_url="redis://localhost:6379/0")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    await manager.start()
    print("✅ Managers started and Redis connected")

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
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
