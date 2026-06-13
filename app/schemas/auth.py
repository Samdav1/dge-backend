from pydantic import BaseModel

class GoogleCallBack(BaseModel):
    id_token: str

    class Config:
        from_attributes = True

class ChangeUserPass(BaseModel):
    password: str
    token: str

    class Config:
        from_attributes = True