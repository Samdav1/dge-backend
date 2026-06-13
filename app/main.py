import uvicorn
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from app.db.session import init_db
import app.models
from app.api.v1 import router as api_router
from app.core.api_key import get_api_key
from app.dependencies.socket_connection import ConnectionManager, manager
from app.middlewares.auth_middleware import AuthMiddleware



@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await manager.start()
    yield
    await manager.stop()


app = FastAPI(
    title="DGE Techs",
    dependencies=[Depends(get_api_key)],
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
