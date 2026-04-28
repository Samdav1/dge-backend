from starlette import status

from app.db.session import get_session
from app.schemas.portfolio import UserPortfolioRead, UserPortfolioCreate, UserPortfolioUpdate, PortfolioMediaRead, \
    PortfolioMediaUpdate
from app.schemas.user import UserRead
from app.dependencies.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel.ext.asyncio.session import AsyncSession

from app.services import portfolio_service
from app.services.portfolio_service import create_portfolio_service, update_portfolio_service, \
    get_user_portfolio_service

router = APIRouter()

@router.post("/create_user_portfolio", response_model=UserPortfolioRead)
async def create_user_portfolio(
        portfolio_info: UserPortfolioCreate,
        db: AsyncSession = Depends(get_session),
        credentials: UserRead = Depends(get_current_user),
        ):
    if not credentials.id:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    try:
        user_id = credentials.id
        user_portfolio = await create_portfolio_service(portfolio_info, db, user_id)
        return user_portfolio
    except Exception as error:
        raise HTTPException(status_code=404, detail=f"Error Creating Profile, {str(error)}")

@router.patch("/update_user_portfolio", response_model=UserPortfolioRead)
async def update_user_portfolio(
        portfolio_info: UserPortfolioUpdate,
        db: AsyncSession = Depends(get_session),
        credentials: UserRead = Depends(get_current_user),
        ):
    if not credentials.id:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        user_id = credentials.id
        user_portfolio = await update_portfolio_service(portfolio_info, db, user_id)
        return user_portfolio
    except Exception as error:
        raise HTTPException(status_code= 500, detail=f"Error Updating Profile, {str(error)}")

@router.post("/create_portfolio_media", response_model=PortfolioMediaRead, status_code=status.HTTP_201_CREATED)
async def upload_portfolio_media(
    portfolio_id,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    current_user: UserRead = Depends(get_current_user)
    ):
    new_media = await portfolio_service.create_portfolio_media_service(
        db=db,
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        file=file
    )
    return new_media


@router.patch("/update_portfolio_media", response_model=PortfolioMediaRead)
async def update_portfolio_media(
    media_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    current_user: UserRead = Depends(get_current_user),
    ):
    if not current_user.id:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    try:
        updated_media = await portfolio_service.update_portfolio_media_service(
            db=db,
            user_id=current_user.id,
            media_update=media_file,
        )
    except Exception as error:
        raise HTTPException(status_code= 500, detail=f"Error Updating Portfolio Media, {str(error)}")
    return updated_media

@router.get("/get_user_portfolio", response_model=UserPortfolioRead)
async def get_user_portfolio(db: AsyncSession = Depends(get_session), current_user: UserRead = Depends(get_current_user)):
    """

    :param db:
    :param current_user:
    """

    if not current_user.id:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
        user_portfolio = await get_user_portfolio_service(db, current_user.id)
        return user_portfolio
