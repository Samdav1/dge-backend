# app/api/v1/transactions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import NoResultFound
from typing import List
from uuid import UUID
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.repositories.transactions_repo import TransactionRepository
from app.schemas.user import UserRead
from app.services.transactions_service import TransactionService
from app.schemas.transactions import TransactionCreate, TransactionRead, TransactionUpdate


router = APIRouter(prefix="/transactions", )


@router.post("/", response_model=TransactionRead)
async def create_transaction(payload: TransactionCreate, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    repo = TransactionRepository(db)
    service = TransactionService(repo)
    return await service.create_transaction(payload)


@router.get("/{txn_id}", response_model=TransactionRead)
async def get_transaction(txn_id: UUID, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    repo = TransactionRepository(db)
    service = TransactionService(repo)
    txn = await service.get_transaction(str(txn_id))
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.get("/user/", response_model=List[TransactionRead])
async def get_user_transactions(current_user: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    repo = TransactionRepository(db)
    service = TransactionService(repo)
    return await service.get_user_transactions(str(current_user.id))


@router.put("/{txn_id}", response_model=TransactionRead)
async def update_transaction(txn_id: UUID, payload: TransactionUpdate, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    repo = TransactionRepository(db)
    service = TransactionService(repo)
    try:
        return await service.update_transaction(str(txn_id), payload)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Transaction not found")


@router.delete("/{txn_id}")
async def delete_transaction(txn_id: UUID, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    repo = TransactionRepository(db)
    service = TransactionService(repo)
    try:
        return await service.delete_transaction(str(txn_id))
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Transaction not found")
