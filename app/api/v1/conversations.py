from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.repositories.conversation_repo import ConversationParticipantRepository
from app.schemas.user import UserRead
from app.schemas.conversation import ConversationCreate, ConversationRead, ConversationParticipantRead, \
    ConversationParticipantCreate
from app.services.conversation_service import create_conversation_service, ConversationParticipantService, get_user_conversation_service

router = APIRouter()


@router.post("/create_conversations", response_model=ConversationRead)
async def create_conversation(
        conversation: ConversationCreate,
        db: AsyncSession = Depends(get_session),
        current_user: UserRead = Depends(get_current_user),
):
    """

    :param conversation:
    :param db:
    :param current_user:
    :return:
    """
    new_conversation = await create_conversation_service(db, conversation, current_user.id)
    return new_conversation

@router.get("/conversations", response_model=List[ConversationRead])
async def get_user_conversations(current_user: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    """

    :param current_user:
    :param db:
    """

    result = await get_user_conversation_service(current_user.id, db)
    return result


@router.post("/add_conversation_participant", response_model=ConversationParticipantRead)
async def add_participant(
        payload: ConversationParticipantCreate,
        current_user: UserRead = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
):
    """

    :param payload:
    :param db:
    :return:
    """
    repo = ConversationParticipantRepository(db)
    service = ConversationParticipantService(repo)
    return await service.add_participant(payload, current_user.id)


@router.get("/get_conversation_participant/{conversation_id}", response_model=list[ConversationParticipantRead])
async def list_participants(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """

    :param conversation_id:
    :param db:
    :return:
    """
    repo = ConversationParticipantRepository(db)
    service = ConversationParticipantService(repo)
    return await service.get_conversation_participants(conversation_id)