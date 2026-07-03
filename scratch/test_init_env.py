import os
# Check if REDIS_URL is in environment before importing app
print("REDIS_URL before import:", os.getenv("REDIS_URL"))

from app.dependencies.socket_connection import manager

print("REDIS_URL after import:", os.getenv("REDIS_URL"))
print("Manager redis_url:", manager.redis_url)
