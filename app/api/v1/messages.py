# app/api/v1/messages.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.repositories.messages_repo import MessageRepository
from app.schemas.user import UserRead
from app.services.messages_service import MessageService
from app.schemas.messages import MessageCreate, MessageRead, MessageUpdate


router = APIRouter(prefix="/messages", )


@router.post("/", response_model=MessageRead)
async def create_message(payload: MessageCreate, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    repo = MessageRepository(db)
    service = MessageService(repo)
    return await service.create_message(payload)


@router.get("/{conversation_id}", response_model=List[MessageRead])
async def get_conversation_messages(conversation_id: str, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    repo = MessageRepository(db)
    service = MessageService(repo)
    return await service.get_conversation_messages(conversation_id)


@router.get("/single/{message_id}", response_model=MessageRead)
async def get_message(message_id: str, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    repo = MessageRepository(db)
    service = MessageService(repo)
    message = await service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.put("/{message_id}", response_model=MessageRead)
async def update_message(message_id: str, payload: MessageUpdate, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    repo = MessageRepository(db)
    service = MessageService(repo)
    return await service.update_message(message_id, payload)


@router.delete("/{message_id}")
async def delete_message(message_id: str, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    repo = MessageRepository(db)
    service = MessageService(repo)
    return await service.delete_message(message_id)
