import uvicorn
from fastapi import FastAPI
from app.db.session import engine
from sqlmodel import SQLModel
import app.models
from app.api.v1 import router as api_router


app = FastAPI(title="DGE Techs")
app.include_router(api_router)


SQLModel.metadata.create_all(bind=engine)



@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)