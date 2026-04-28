from app.db.session import get_session
from app.schemas.user import UserRead
from app.dependencies.auth import get_current_user
from app.models.wallet import Wallet, WalletType
from app.services.wallet_service import create_user_wallet_service, update_user_wallet_service, get_user_wallet_service
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.wallet import WalletCreate, WalletUpdate, WalletRead
router = APIRouter()

@router.post('/create_wallet', response_model=WalletRead)
async def create_wallet(
        db: AsyncSession = Depends(get_session),
        credentials: UserRead = Depends(get_current_user)
        ):
    if not credentials.id:
        raise HTTPException(detail="Missing user id", status_code=404)
    user = credentials.id
    try:
        user_deposit_wallet = await create_user_wallet_service(db, user)
        return WalletRead.model_validate(user_deposit_wallet)
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=500)

@router.patch('/update_wallet', response_model=WalletRead, tags=['Update Wallet'])
async def update_wallet(
        wallet_type: WalletType,
        amount: float, db: AsyncSession = Depends(get_session),
        credentials: UserRead = Depends(get_current_user)
):
    if not credentials.id:
        raise HTTPException(detail="Missing user id", status_code=404)
    user = credentials.id
    try:
        user_deposit_wallet = await update_user_wallet_service(db, user, amount, wallet_type )
        return WalletRead.model_validate(user_deposit_wallet)
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=500)

@router.get("/get_user_wallet", response_model=list[WalletRead])
async def get_user_wallet(
        db: AsyncSession = Depends(get_session),
        credentials: UserRead = Depends(get_current_user)
):
    """

    :param db:
    :param credentials:
    """
    if not credentials.id:
        raise HTTPException(detail="Missing user id", status_code=404)
    user = credentials.id

    wallets = await get_user_wallet_service(db, user)
    return wallets