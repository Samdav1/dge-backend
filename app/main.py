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

import os
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
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
