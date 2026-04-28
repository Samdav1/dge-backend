from app.repositories.portfolio_repo import create_portfolio_repo, update_portfolio_repo
from app.schemas.portfolio import UserPortfolioRead, UserPortfolioCreate, UserPortfolioUpdate, PortfolioMediaUpdate
import uuid
from fastapi import UploadFile, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from app.dependencies.file_handler import save_avatar
from app.repositories import portfolio_repo
from app.schemas.portfolio import PortfolioMediaCreate, PortfolioMediaRead

async def create_portfolio_service(portfolio_info: UserPortfolioCreate, db: AsyncSession, user_id) -> UserPortfolioRead:
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        user_portfolio = await create_portfolio_repo(portfolio_info, db=db, user_id=user_id)
        return user_portfolio
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

async def update_portfolio_service(portfolio_info: UserPortfolioUpdate, db: AsyncSession, user_id) -> UserPortfolioRead:
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        user_portfolio_update = await update_portfolio_repo(portfolio_info, db=db, user_id=user_id)
        return user_portfolio_update
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))



async def create_portfolio_media_service(
        db: AsyncSession, *, portfolio_id: uuid.UUID, user_id: uuid.UUID, file: UploadFile) -> PortfolioMediaRead:
    await portfolio_repo.get_portfolio_by_id_and_owner(
        db=db, portfolio_id=portfolio_id, user_id=user_id
    )
    s3_key = await save_avatar(file)
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
    s3_key = await save_avatar(media_update)
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

async def get_user_portfolio_service(db: AsyncSession, user_id) -> UserPortfolioRead:
    """

    :param db:
    :param user_id:
    """

    if user_id:
        portfolio= await portfolio_repo.get_portfolio_repo(db, user_id)
        return portfolio
    else:
        raise HTTPException(status_code=404, detail="User not found")
