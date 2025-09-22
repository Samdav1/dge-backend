import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    database_uri: str = os.getenv("DB_URI")

    class Config:
        env_file = ".env"

settings = Settings()
