import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file relative to this file's location
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
