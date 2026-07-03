import redis
import os
from dotenv import load_dotenv

# Load env file
load_dotenv()

redis_url = os.getenv("REDIS_URL")
print(f"Connecting to Redis URL: {redis_url}")

try:
    r = redis.Redis.from_url(redis_url, decode_responses=True)
    success = r.set('foo', 'bar')
    result = r.get('foo')
    print(f"Set success: {success}, Get result: {result}")
    if result == 'bar':
        print("✅ Redis Connection Successful!")
    else:
        print("❌ Redis Get returned incorrect value.")
except Exception as e:
    print(f"❌ Redis Connection Failed: {e}")
