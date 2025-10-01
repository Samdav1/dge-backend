from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.repositories.conversation_repo import ConversationParticipantRepository
from app.schemas.user import UserRead
from app.schemas.conversation import ConversationCreate, ConversationRead, ConversationParticipantRead, \
    ConversationParticipantCreate
from app.services.conversation_service import create_conversation_service, ConversationParticipantService

router = APIRouter()


@router.post("/create_conversations", response_model=ConversationRead)
async def create_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_session),
    current_user: UserRead = Depends(get_current_user),
):

    new_conversation = await create_conversation_service(db, conversation, current_user.id)
    return new_conversation

@router.post("/add_conversation_participant", response_model=ConversationParticipantRead)
async def add_participant(
    payload: ConversationParticipantCreate,
    db: AsyncSession = Depends(get_session),
):
    repo = ConversationParticipantRepository(db)
    service = ConversationParticipantService(repo)
    return await service.add_participant(payload)


@router.get("/get_conversation_participant/{conversation_id}", response_model=list[ConversationParticipantRead])
async def list_participants(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    repo = ConversationParticipantRepository(db)
    service = ConversationParticipantService(repo)
    return await service.get_conversation_participants(conversation_id)