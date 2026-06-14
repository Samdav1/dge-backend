import asyncio
from app.db.session import get_session
from app.models.user import Users
from app.models.wallet import Wallet, WalletType
from sqlalchemy import select

async def main():
    async for session in get_session():
        db = session
        break
    
    # Get user
    stmt = select(Users).where(Users.email == "adoxop1@gmail.com")
    res = await db.exec(stmt)
    user = res.scalars().first()
    
    if not user:
        print("User adoxop1@gmail.com not found!")
        return
        
    print(f"Found user: {user.username} (ID: {user.id})")
    
    # Get deposit wallet or create it
    stmt_wallet = select(Wallet).where(
        Wallet.user_id == user.id,
        Wallet.wallet_type == WalletType.deposit
    )
    res_wallet = await db.exec(stmt_wallet)
    wallet = res_wallet.scalars().first()
    
    if not wallet:
        print("Deposit wallet not found, creating one...")
        wallet = Wallet(
            user_id=user.id,
            wallet_type=WalletType.deposit,
            balance_cents=0.0,
            currency="USD"
        )
        db.add(wallet)
    
    # 1 billion USD = 100,000,000,000 cents
    billion_cents = 1_000_000_000 * 100
    wallet.balance_cents = float(billion_cents)
    db.add(wallet)
    
    # Let's also make sure their earnings wallet has it if they want
    stmt_earnings = select(Wallet).where(
        Wallet.user_id == user.id,
        Wallet.wallet_type == WalletType.earnings
    )
    res_earnings = await db.exec(stmt_earnings)
    earnings_wallet = res_earnings.scalars().first()
    if not earnings_wallet:
        earnings_wallet = Wallet(
            user_id=user.id,
            wallet_type=WalletType.earnings,
            balance_cents=0.0,
            currency="USD"
        )
        db.add(earnings_wallet)
    
    earnings_wallet.balance_cents = float(billion_cents)
    db.add(earnings_wallet)
    
    await db.commit()
    print("Successfully funded deposit and earnings wallets of adoxop1@gmail.com with 1 billion USD!")

if __name__ == "__main__":
    asyncio.run(main())
