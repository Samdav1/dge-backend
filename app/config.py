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

    # SMTP Configuration Switcher
    email_provider: str = os.getenv("EMAIL_PROVIDER", "google")

    # Google SMTP Settings
    email_host_google: str = os.getenv("EMAIL_HOST_GOOGLE", "smtp.gmail.com")
    email_port_google: int = int(os.getenv("EMAIL_PORT_GOOGLE", "465"))
    email_use_ssl_google: bool = os.getenv("EMAIL_USE_SSL_GOOGLE", "true").lower() == "true"
    username_google: str = os.getenv("USERNAME_GOOGLE", "")
    email_pass_google: str = os.getenv("EMAIL_PASS_GOOGLE", "")
    email_sender_address_google: str = os.getenv("EMAIL_SENDER_ADDRESS_GOOGLE", "")

    # cPanel SMTP Settings
    email_host_cpanel: str = os.getenv("EMAIL_HOST_CPANEL", "")
    email_port_cpanel: int = int(os.getenv("EMAIL_PORT_CPANEL", "465"))
    email_use_ssl_cpanel: bool = os.getenv("EMAIL_USE_SSL_CPANEL", "true").lower() == "true"
    username_cpanel: str = os.getenv("USERNAME_CPANEL", "")
    email_pass_cpanel: str = os.getenv("EMAIL_PASS_CPANEL", "")
    email_sender_address_cpanel: str = os.getenv("EMAIL_SENDER_ADDRESS_CPANEL", "")

    metamap_webhook_secret: str = os.getenv("METAMAP_WEBHOOK_SECRET", "")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
