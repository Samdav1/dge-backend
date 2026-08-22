from app.repositories.portfolio_repo import create_portfolio_repo, update_portfolio_repo
from app.schemas.portfolio import UserPortfolioRead, UserPortfolioCreate, UserPortfolioUpdate, PortfolioMediaUpdate, UserPortfolioWithMediaRead
import uuid
from fastapi import UploadFile, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from app.dependencies.file_handler import save_portfolio_media
from app.repositories import portfolio_repo
from app.schemas.portfolio import PortfolioMediaCreate, PortfolioMediaRead

from app.repositories.user_repo import get_user_by_id
from app.services.email_notification_service import NotificationService

async def create_portfolio_service(portfolio_info: UserPortfolioCreate, db: AsyncSession, user_id) -> UserPortfolioRead:
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        user_portfolio = await create_portfolio_repo(portfolio_info, db=db, user_id=user_id)
        if user_portfolio:
            try:
                user = await get_user_by_id(user_id, db)
                if user:
                    notifier = NotificationService()
                    title = getattr(user_portfolio, 'title', portfolio_info.title if hasattr(portfolio_info, 'title') else 'Portfolio Item')
                    notifier.send_portfolio_updated_mail(user=user, portfolio_title=str(title))
            except Exception as e:
                print(f"Failed to dispatch portfolio created email: {e}")
        return user_portfolio
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

async def update_portfolio_service(portfolio_info: UserPortfolioUpdate, db: AsyncSession, user_id) -> UserPortfolioRead:
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        user_portfolio_update = await update_portfolio_repo(portfolio_info, db=db, user_id=user_id)
        if user_portfolio_update:
            try:
                user = await get_user_by_id(user_id, db)
                if user:
                    notifier = NotificationService()
                    title = getattr(user_portfolio_update, 'title', 'Portfolio Showcase')
                    notifier.send_portfolio_updated_mail(user=user, portfolio_title=str(title))
            except Exception as e:
                print(f"Failed to dispatch portfolio updated email: {e}")
        return user_portfolio_update
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))




async def create_portfolio_media_service(
        db: AsyncSession, *, portfolio_id: uuid.UUID, user_id: uuid.UUID, file: UploadFile) -> PortfolioMediaRead:
    await portfolio_repo.get_portfolio_by_id_and_owner(
        db=db, portfolio_id=portfolio_id, user_id=user_id
    )
    s3_key = await save_portfolio_media(file)
    file_size = file.size

    media_data = PortfolioMediaCreate(
        media_type=file.content_type,
        s3_key=s3_key,
        size_bytes=file_size,
        processed=True
    )

    new_media = await portfolio_repo.create_media_repo(
        db=db, media_data=media_data, portfolio_id=portfolio_id
    )
    return PortfolioMediaRead.model_validate(new_media)


async def update_portfolio_media_service(db: AsyncSession, user_id, media_update: UploadFile) -> PortfolioMediaRead:
    s3_key = await save_portfolio_media(media_update)
    file_size = media_update.size

    media_data = PortfolioMediaUpdate(
        media_type=media_update.content_type,
        s3_key=s3_key,
        size_bytes=file_size,
        processed=True
    )
    updated_media = await portfolio_repo.update_media_repo(
        db=db, user_id=user_id, media_update=media_data
    )
    return PortfolioMediaRead.model_validate(updated_media)

async def delete_portfolio_media_service(db: AsyncSession, *, media_id, user_id) -> bool:
    return await portfolio_repo.delete_media_repo(db=db, media_id=media_id, user_id=user_id)

async def get_user_portfolio_service(db: AsyncSession, user_id) -> UserPortfolioWithMediaRead:
    """

    :param db:
    :param user_id:
    """

    if user_id:
        portfolio= await portfolio_repo.get_portfolio_repo(db, user_id)
        return portfolio
    else:
        raise HTTPException(status_code=404, detail="User not found")
