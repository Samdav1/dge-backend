from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import ConversationParticipant
from app.schemas.conversation import ConversationCreate, ConversationRead, ConversationParticipantCreate, ConversationParticipantRead
from app.repositories.conversation_repo import (
    insert_conversation_into_db, 
    ConversationParticipantRepository, 
    get_user_conversations,
    delete_conversation_for_user
)


async def create_conversation_service(
    db: AsyncSession, conversation_create: ConversationCreate, user_id
    ) -> ConversationRead:
    """

    :param db:
    :param conversation_create:
    :param user_id:
    :return:
    """

    new_conversation = await insert_conversation_into_db(db, conversation_create, user_id)
    return new_conversation

async def get_user_conversation_service(
        user_id: UUID, db: AsyncSession
):
    """

    :param user_id:
    :param db:
    :return:
    """
    result = await get_user_conversations(user_id, db)
    return result

async def delete_conversation_service(conversation_id: UUID, user_id: UUID, db: AsyncSession):
    return await delete_conversation_for_user(conversation_id, user_id, db)


class ConversationParticipantService:
    def __init__(self, repo: ConversationParticipantRepository):
        self.repo = repo

    async def add_participant(self, data: ConversationParticipantCreate, user_id: UUID) -> ConversationParticipantRead:
        new_participant = ConversationParticipant(
            conversation_id=data.conversation_id,
            user_id=data.user_id,
            role=data.role,
        )
        await self.repo.add_participant(new_participant)
        new_participant2 = ConversationParticipant(
            conversation_id=data.conversation_id,
            user_id=user_id,
            role=data.role,
        )

        return await self.repo.add_participant(new_participant2)

    async def get_conversation_participants(self, conversation_id):
        return await self.repo.get_participants_by_conversation(conversation_id)
