import uvicorn
from fastapi import FastAPI
from api.v1 import users
from app.db.session import engine
from sqlmodel import SQLModel
import app.models


app = FastAPI(title="DGE Techs")

SQLModel.metadata.create_all(bind=engine)

app.include_router(users.router, prefix="/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)