from sqlalchemy.orm import selectinload

from app.models import Users
from app.schemas.portfolio import UserPortfolioRead, UserPortfolioCreate, UserPortfolioUpdate, PortfolioMediaCreate, \
    PortfolioMediaRead, PortfolioMediaUpdate
from app.models.portfolio import UserPortfolio, PortfolioMedia
from fastapi import HTTPException, status, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

async def create_portfolio_repo(portfolio_info: UserPortfolioCreate, db:AsyncSession,  user_id) -> UserPortfolioRead:
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    try:
        #Creating User Portfolio
        user_portfolio = UserPortfolio(
            user_id=user_id,
            title=portfolio_info.title,
            description=portfolio_info.description,
            category=portfolio_info.category,
        )
        db.add(user_portfolio)
        await db.commit()
        await db.refresh(user_portfolio)

        refined_user_portfolio= UserPortfolioRead.model_validate(user_portfolio)
        return refined_user_portfolio
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        )


async def update_portfolio_repo(portfolio_info: UserPortfolioUpdate, db:AsyncSession, user_id) -> UserPortfolioRead:
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cannot Get Current User")
    statement = select(UserPortfolio).where(UserPortfolio.user_id == user_id)
    result = await db.exec(statement)
    user_portfolio = result.first()
    portfolio_data = portfolio_info.model_dump(exclude_unset=True)

    for key, value in portfolio_data.items():
        if hasattr(user_portfolio, key):
            if key == "visibility":
                setattr(user_portfolio, key, value)
            else:
                setattr(user_portfolio, key, str(value))

    try:
        db.add(user_portfolio)
        await db.commit()
        await db.refresh(user_portfolio)
        refined_user_portfolio= UserPortfolioRead.model_validate(user_portfolio)
        return refined_user_portfolio
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Cannot Update UserPortfolio: {str(e)}")

async def get_portfolio_by_id_and_owner(db: AsyncSession, *, portfolio_id, user_id) -> UserPortfolioRead:
    statement = select(UserPortfolio).where(
        UserPortfolio.id == portfolio_id,
        UserPortfolio.user_id == user_id
    )
    result = await db.exec(statement)
    portfolio = result.first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or you do not have permission to access it."
        )
    refined_portfolio = UserPortfolioRead.model_validate(portfolio)
    return refined_portfolio

async def create_media_repo(
    db: AsyncSession, *, media_data: PortfolioMediaCreate, portfolio_id) -> PortfolioMediaRead:

    db_media = PortfolioMedia(
        **media_data.model_dump(),
        portfolio_id=portfolio_id
    )
    db.add(db_media)
    await db.commit()
    await db.refresh(db_media)
    refined_media= PortfolioMediaRead.model_validate(db_media)
    return refined_media


async def update_media_repo(
        db: AsyncSession, user_id, media_update: PortfolioMediaUpdate
        ) -> PortfolioMediaRead:
    update_data = media_update.model_dump(exclude_unset=True)
    statement = select(Users).options(selectinload(Users.portfolios).selectinload(UserPortfolio.media_files)).where(Users.id == user_id)
    result = await db.exec(statement)
    db_media = result.first()
    media = None
    for portfolio in db_media.portfolios:
        for media_file in portfolio.media_files:
            media = media_file
            break
        if media:
            break
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
        )

    print("testing ultra linking", media)

    for key, value in update_data.items():
        setattr(media, key, value)

    try:
        db.add(media)
        await db.commit()
        await db.refresh(media)
        refined_media=PortfolioMediaRead.model_validate(media)
        print("aftereffect")
        return refined_media
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot Update Media: {str(e)}")

async def get_portfolio_repo(db: AsyncSession, user_id) -> UserPortfolioRead:
    """

    :param db:
    :param user_id:
    :return:
    """
    statement = select(UserPortfolio).options(selectinload(UserPortfolio.media_files)).where(
        UserPortfolio.user_id == user_id
    )
    result = await db.exec(statement)
    portfolio = result.first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or you do not have permission to access it."
        )
    refined_portfolio = UserPortfolioRead.model_validate(portfolio)
    return refined_portfolio