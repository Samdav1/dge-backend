from app.models import Wallet
from app.schemas.wallet import WalletCreate, WalletRead, WalletType
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, Depends
from app.repositories.wallet_repo import create_user_wallet_repo, update_user_wallet_balance_repo


async def create_user_wallet_service(db: AsyncSession, user_id) -> WalletRead:
    if not user_id:
        raise HTTPException(detail="Missing user id", status_code=404)
    try:
        wallet = await create_user_wallet_repo(db, user_id)
        return WalletRead.model_validate(wallet)
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=500)

async def update_user_wallet_service(db: AsyncSession, user_id, amount: float, wallet_type: WalletType ) -> WalletRead:
    if not user_id:
        raise HTTPException(detail="Missing user id", status_code=404)
    try:
        wallet = await update_user_wallet_balance_repo(db, user_id, amount, wallet_type)
        return WalletRead.model_validate(wallet)
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=500)