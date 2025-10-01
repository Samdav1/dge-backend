from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import ConversationParticipant
from app.schemas.conversation import ConversationCreate, ConversationRead, ConversationParticipantCreate, ConversationParticipantRead
from app.repositories.conversation_repo import insert_conversation_into_db, ConversationParticipantRepository


async def create_conversation_service(
    db: AsyncSession, conversation_create: ConversationCreate, user_id
    ) -> ConversationRead:
    new_conversation = await insert_conversation_into_db(db, conversation_create, user_id)
    return new_conversation

class ConversationParticipantService:
    def __init__(self, repo: ConversationParticipantRepository):
        self.repo = repo

    async def add_participant(self, data: ConversationParticipantCreate) -> ConversationParticipantRead:
        new_participant = ConversationParticipant(
            conversation_id=data.conversation_id,
            user_id=data.user_id,
            role=data.role,
        )
        return await self.repo.add_participant(new_participant)

    async def get_conversation_participants(self, conversation_id):
        return await self.repo.get_participants_by_conversation(conversation_id)
