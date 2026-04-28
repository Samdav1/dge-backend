import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    database_uri: str = os.getenv("DB_URI")
    agora_app_id: str = os.getenv("AGORA_APP_ID", "")
    agora_app_certificate: str = os.getenv("AGORA_APP_CERTIFICATE", "")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
