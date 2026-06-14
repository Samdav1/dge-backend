import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    database_uri: str = os.getenv("DB_URI")
    agora_app_id: str = os.getenv("AGORA_APP_ID", "")
    agora_app_certificate: str = os.getenv("AGORA_APP_CERTIFICATE", "")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    api_url: str = os.getenv("API_URL", "http://127.0.0.1:8000")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
