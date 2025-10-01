from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from sqlmodel import select

from app.models.conversation import Conversation, ConversationParticipant
from app.schemas.conversation import ConversationCreate, ConversationRead, ConversationParticipantCreate, \
    ConversationParticipantRead


async def insert_conversation_into_db(
    db: AsyncSession, conversation_create: ConversationCreate, user_id
    ) -> ConversationRead:
    try:
        conversation = Conversation(
            title=conversation_create.title,
            type=conversation_create.type.value,  # Enum → str
            created_by=user_id,
            metadataInfo=conversation_create.metadataInfo or {},
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return ConversationRead.model_validate(conversation)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

class ConversationParticipantRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_participant(self, participant: ConversationParticipant) -> ConversationParticipantRead:
        self.db.add(participant)
        await self.db.commit()
        await self.db.refresh(participant)
        participant_dict = participant.model_dump()
        refined_participant = ConversationParticipantRead.model_validate(participant_dict)
        return refined_participant

    async def get_participants_by_conversation(self, conversation_id: UUID) -> list[ConversationParticipant]:
        statement = select(ConversationParticipant).where(ConversationParticipant.conversation_id == conversation_id)
        result = await self.db.exec(statement)
        return result.all()