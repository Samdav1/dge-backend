from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import NoResultFound
from app.models.transactions import Transaction
from app.schemas.transactions import TransactionCreate, TransactionUpdate


class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_transaction(self, payload: TransactionCreate) -> Transaction:
        txn = Transaction(**payload.dict())
        self.db.add(txn)
        await self.db.commit()
        await self.db.refresh(txn)
        return txn

    async def create_transaction_ext(self, payload: TransactionCreate) -> Transaction:
        txn = Transaction(**payload.dict())
        self.db.add(txn)
        return txn

    async def get_transaction(self, txn_id: str) -> Transaction | None:
        stmt = select(Transaction).where(Transaction.id == txn_id)
        result = await self.db.exec(stmt)
        return result.first()

    async def get_transactions_by_user(self, user_id: str) -> list[Transaction]:
        stmt = select(Transaction).where(Transaction.users_id == user_id).order_by(Transaction.id.desc())
        result = await self.db.exec(stmt)
        return result.all()

    async def update_transaction(self, txn_id: str, payload: TransactionUpdate) -> Transaction:
        txn = await self.get_transaction(txn_id)
        if not txn:
            raise NoResultFound(f"Transaction {txn_id} not found")

        for key, value in payload.dict(exclude_unset=True).items():
            setattr(txn, key, value)

        self.db.add(txn)
        await self.db.commit()
        await self.db.refresh(txn)
        return txn

    async def delete_transaction(self, txn_id: str) -> dict:
        txn = await self.get_transaction(txn_id)
        if not txn:
            raise NoResultFound(f"Transaction {txn_id} not found")

        await self.db.delete(txn)
        await self.db.commit()
        return {"deleted": True, "transaction_id": txn_id}