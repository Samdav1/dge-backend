from typing import List
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from sqlmodel import select

from datetime import datetime, timezone
from app.models.conversation import Conversation, ConversationParticipant
from app.schemas.conversation import ConversationCreate, ConversationRead, ConversationParticipantCreate, \
    ConversationParticipantRead


async def delete_conversation_for_user(conversation_id: UUID, user_id: UUID, db: AsyncSession):
    stmt = select(ConversationParticipant).where(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == user_id
    )
    result = await db.exec(stmt)
    participant = result.first()
    if participant:
        participant.left_at = datetime.now(timezone.utc)
        db.add(participant)
        await db.commit()
        return True
    return False


async def insert_conversation_into_db(
    db: AsyncSession, conversation_create: ConversationCreate, user_id
    ) -> ConversationRead:
    """

    :param db:
    :param conversation_create:
    :param user_id:
    :return:
    """

    result = None
    if conversation_create.recipient_id:
        result = await check_negotiation_existence(
            user_id=user_id,
            db=db,
            recipient_id=conversation_create.recipient_id,
            conversation_type=conversation_create.type.value
        )
    print(f"result++++++++++++++: {result}")
    if result is not None:
        return result
    else:

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

            # Add participants
            participant1 = ConversationParticipant(
                conversation_id=conversation.id,
                user_id=user_id,
                role="admin"
            )
            db.add(participant1)

            if conversation_create.recipient_id:
                participant2 = ConversationParticipant(
                    conversation_id=conversation.id,
                    user_id=conversation_create.recipient_id,
                    role="member"
                )
                db.add(participant2)

            await db.commit()
            await db.refresh(conversation)

            return ConversationRead.model_validate(conversation)
        except SQLAlchemyError as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

async def get_user_conversations(user_id: UUID, db: AsyncSession) -> List[ConversationRead]:
    """

    :param user_id:
    :param db:
    :return:
    """
    conversation_list = []
    stmt = select(ConversationParticipant).where(
        ConversationParticipant.user_id == user_id,
        ConversationParticipant.left_at.is_(None)
        ).options(selectinload(ConversationParticipant.conversation))
    result = await db.exec(stmt)
    payload = result.all()
    if payload:
        for conversation in payload:
            conversation_list.append(ConversationRead.model_validate(conversation.conversation))
    return conversation_list


async def check_negotiation_existence(
        user_id: UUID,
        recipient_id: UUID,
        db: AsyncSession,
        conversation_type: str = "private"
) -> ConversationRead | None:
    """
    Check if a shared conversation exists between two users.
    """
    # 1. Find conversation IDs for USER (Use scalars to get actual UUIDs, not tuples)
    user_convs_stmt = select(ConversationParticipant.conversation_id).where(
        ConversationParticipant.user_id == user_id
    )
    user_convs_result = await db.exec(user_convs_stmt)
    # .scalars() extracts the value from the row (tuple)
    user_conv_ids = set(user_convs_result.all())

    if not user_conv_ids:
        return None

    # 2. Find conversation IDs for RECIPIENT
    recipient_convs_stmt = select(ConversationParticipant.conversation_id).where(
        ConversationParticipant.user_id == recipient_id
    )
    recipient_convs_result = await db.exec(recipient_convs_stmt)
    recipient_conv_ids = set(recipient_convs_result.all())

    if not recipient_conv_ids:
        return None

    # 3. Find intersection (common conversations)
    common_conv_ids = user_conv_ids.intersection(recipient_conv_ids)

    if not common_conv_ids:
        return None

    # 4. Check each common conversation for type match
    for conversation_id in common_conv_ids:
        conv_stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.type == conversation_type
        )
        conv_result = await db.exec(conv_stmt)
        conversation = conv_result.first()

        if conversation:
            return ConversationRead.model_validate(conversation)

    return None

class ConversationParticipantRepository:
    """

    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_participant(self, participant: ConversationParticipant) -> ConversationParticipantRead:
        """

        :param participant:
        :return:
        """
        self.db.add(participant)
        await self.db.commit()
        await self.db.refresh(participant)
        participant_dict = participant.model_dump()
        refined_participant = ConversationParticipantRead.model_validate(participant_dict)
        return refined_participant

    async def get_participants_by_conversation(self, conversation_id: UUID) -> list[ConversationParticipant]:
        """

        :param conversation_id:
        :return:
        """
        statement = select(ConversationParticipant).where(ConversationParticipant.conversation_id == conversation_id)
        result = await self.db.exec(statement)
        return result.all()

    async def check_negotiation_existence(self, user_id: UUID, recipient_id: UUID, db: AsyncSession):
        """

        :param user_id:
        :param db:
        :return:
        """
        conversation_list = []
        conversation_list_b = []
        stmt = select(ConversationParticipant).where(
            ConversationParticipant.user_id == user_id
        ).options(selectinload(ConversationParticipant.conversation))

        stmt_b = select(ConversationParticipant).where(
            ConversationParticipant.user_id == recipient_id
        ).options(selectinload(ConversationParticipant.conversation))

        result = await db.exec(stmt)
        result_b = await db.exec(stmt_b)
        payload_b = result_b.all()
        payload = result.all()

        if payload:
            for conversation in payload:
                conversation_list.append(ConversationRead.model_validate(conversation.conversation))

        if payload_b:
            for conversation in payload_b:
                conversation_list_b.append(ConversationRead.model_validate(conversation.conversation))

        for b in conversation_list:
            if b.id not in conversation_list_b:
                return False
            else:
                return b
