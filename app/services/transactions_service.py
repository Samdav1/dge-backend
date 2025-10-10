# app/services/transaction_service.py
from app.repositories.transactions_repo import TransactionRepository
from app.schemas.transactions import TransactionCreate, TransactionUpdate


class TransactionService:
    def __init__(self, repo: TransactionRepository):
        self.repo = repo

    async def create_transaction(self, payload: TransactionCreate):
        return await self.repo.create_transaction(payload)

    async def get_transaction(self, txn_id: str):
        return await self.repo.get_transaction(txn_id)

    async def get_user_transactions(self, user_id: str):
        return await self.repo.get_transactions_by_user(user_id)

    async def update_transaction(self, txn_id: str, payload: TransactionUpdate):
        return await self.repo.update_transaction(txn_id, payload)

    async def delete_transaction(self, txn_id: str):
        return await self.repo.delete_transaction(txn_id)
