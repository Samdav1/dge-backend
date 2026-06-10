import os
import asyncio
import anyio
from typing import Callable, Any

def dispatch_task(celery_task: Any, sync_func: Callable, *args, **kwargs):
    """
    Dispatches a task to Celery or runs it locally via asyncio/anyio
    depending on the BACKGROUND_TASK_RUNNER environment variable.
    
    :param celery_task: The Celery task object (which has a .delay() method).
    :param sync_func: The actual synchronous function to run if using local background execution.
    :param args: Positional arguments for the task.
    :param kwargs: Keyword arguments for the task.
    """
    runner = os.getenv("BACKGROUND_TASK_RUNNER", "celery").lower()
    
    if runner == "fastapi":
        # Simulate FastAPI Background Tasks behavior for synchronous functions.
        # This executes the synchronous function in a separate thread without blocking the event loop.
        def _runner():
            try:
                sync_func(*args, **kwargs)
            except Exception as e:
                import logging
                logging.error(f"Error executing background task {sync_func.__name__}: {e}")

        try:
            # We must be running inside an event loop for create_task to work.
            asyncio.get_running_loop()
            asyncio.create_task(anyio.to_thread.run_sync(_runner))
        except RuntimeError:
            # Fallback if no event loop is running (e.g., synchronous context)
            import threading
            thread = threading.Thread(target=_runner)
            thread.start()
    else:
        # Default to Celery
        celery_task.delay(*args, **kwargs)
