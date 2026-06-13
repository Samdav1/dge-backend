from app.dependencies.auth import get_current_user
from app.schemas.wallet import WalletCreate, WalletUpdate, WalletRead, WalletBase
from  sqlmodel.ext.asyncio.session import AsyncSession
from app.models.wallet import Wallet, WalletType
from fastapi import Depends, HTTPException
from app.schemas.user import UserRead
from sqlmodel import select


async def create_user_wallet_repo(db: AsyncSession, credentials) -> WalletRead:
    if not credentials:
        raise HTTPException(detail="Missing user id", status_code=404)
    user_id = credentials
    user_deposit_wallet = Wallet(user_id=user_id, wallet_type=WalletType.deposit, currency="NGN")
    user_earnings_wallet = Wallet(user_id=user_id, wallet_type=WalletType.earnings, currency="NGN")
    try:
        db.add(user_deposit_wallet)
        db.add(user_earnings_wallet)
        await db.commit()
        await db.refresh(user_deposit_wallet)
        await db.refresh(user_earnings_wallet)
        serialized_wallet = WalletRead.model_validate(user_deposit_wallet)
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=500)
    return serialized_wallet


async def update_user_wallet_balance_repo(
    db: AsyncSession, credentials, amount: float, wallet_type: WalletType
) -> WalletRead:
    if not credentials:
        raise HTTPException(status_code=400, detail="Missing user id")

    statement = select(Wallet).where(
        Wallet.user_id == credentials, Wallet.wallet_type == wallet_type
    )
    result = await db.exec(statement)
    wallet = result.first()

    if not wallet:
        raise HTTPException(status_code=404, detail="User Wallet doesn't exist")

    try:
        if amount < 0 and wallet.balance_cents + amount < 0:
            raise HTTPException(
                status_code=400,
                detail="Insufficient funds: cannot complete transaction"
            )

        wallet.balance_cents += int(amount)
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)

        return WalletRead.model_validate(wallet)
    except HTTPException:
        raise
    except Exception as e:

        raise HTTPException(status_code=500, detail=f"Error updating wallet: {str(e)}")


async def update_user_wallet_balance_repo_ext(
    db: AsyncSession, credentials, amount: float, wallet_type: WalletType, allow_negative: bool = False
) -> WalletRead:
    if not credentials:
        raise HTTPException(status_code=400, detail="Missing user id")

    statement = select(Wallet).where(
        Wallet.user_id == credentials, Wallet.wallet_type == wallet_type
    )
    result = await db.exec(statement)
    wallet = result.first()

    if not wallet:
        # Auto-create the missing wallet
        wallet = Wallet(
            user_id=credentials,
            wallet_type=wallet_type,
            balance_cents=0,
            currency="NGN"
        )
        db.add(wallet)
        await db.flush()

    try:
        if not allow_negative and amount < 0 and wallet.balance_cents + amount < 0:
            raise HTTPException(
                status_code=400,
                detail="Insufficient funds: cannot complete transaction"
            )

        wallet.balance_cents += int(amount)
        db.add(wallet)

        return WalletRead.model_validate(wallet)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating wallet: {str(e)}")


async def get_user_wallet_repo(db: AsyncSession, credentials) -> list[WalletRead]:
    """

    :p
    :
    :param credentials:
    """

    user_wallet = []

    if not credentials:
        raise HTTPException(status_code=404, detail="Missing user id")

    try:
        stmt = select(Wallet).where(Wallet.user_id == credentials)
        result = await db.exec(stmt)
        payload = result.all()

        for w in payload:
            wallet = WalletRead.model_validate(w)
            user_wallet.append(wallet)
        return user_wallet
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user wallet: {str(e)}")
