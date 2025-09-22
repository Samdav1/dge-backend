import uvicorn
from fastapi import FastAPI
from api.v1 import users
app = FastAPI(title="DGE Techs")

app.include_router(users.router, prefix="/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)