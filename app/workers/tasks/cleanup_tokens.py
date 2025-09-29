from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session
from app.repositories.refresh_token_repo import delete_expired
from app.db.session import get_session

def cleanup_tokens(db: AsyncSession = Depends(get_session)):
        deleted_count = delete_expired(db)
        print(f"Cleanup job removed {deleted_count} expired/revoked tokens")

def start_cleanup_job():
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_tokens, "interval", hours=1)  # run every hour
    scheduler.start()
