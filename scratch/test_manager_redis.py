import asyncio
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

from app.dependencies.socket_connection import ConnectionManager

async def test_manager():
    redis_url = os.getenv("REDIS_URL")
    print(f"Testing ConnectionManager with REDIS_URL: {redis_url}")
    
    manager = ConnectionManager(redis_url=redis_url)
    
    try:
        await manager.start()
        print("Manager start() call completed.")
        
        # Let's wait a bit to let the background task run
        await asyncio.sleep(3)
        
        # Check background task status
        task = manager._pubsub_task
        if task:
            if task.done():
                exc = task.exception()
                if exc:
                    print(f"❌ Background task failed with exception: {exc}")
                else:
                    print("❌ Background task finished unexpectedly (no exception).")
            else:
                print("✅ Background task is running fine!")
        else:
            print("❌ No background task was started.")
            
    except Exception as e:
        print(f"❌ manager.start() failed: {e}")
    finally:
        await manager.stop()

if __name__ == "__main__":
    asyncio.run(test_manager())
