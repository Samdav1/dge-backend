from pydantic import BaseModel, ConfigDict

class GoogleCallBack(BaseModel):
    id_token: str

    model_config = ConfigDict(from_attributes=True)
class ChangeUserPass(BaseModel):
    password: str
    token: str

    model_config = ConfigDict(from_attributes=True)
