# app/repositories/message_repo.py
from sqlmodel import select
from app.models.messages import Message
from app.schemas.messages import MessageCreate, MessageUpdate
from sqlalchemy.exc import NoResultFound


class MessageRepository:
    def __init__(self, db):
        self.db = db

    async def create_message(self, message: MessageCreate):
        db_message = Message(**message.dict())
        self.db.add(db_message)
        await self.db.commit()
        await self.db.refresh(db_message)
        return db_message

    async def get_messages_by_conversation(self, conversation_id: str):
        statement = select(Message).where(Message.conversation_id == conversation_id)
        result = await self.db.exec(statement)
        return result.all()

    async def get_message_by_id(self, message_id: str):
        statement = select(Message).where(Message.id == message_id)
        result = await self.db.exec(statement)
        return result.first()

    async def update_message(self, message_id: str, payload: MessageUpdate):
        db_message = await self.get_message_by_id(message_id)
        if not db_message:
            raise NoResultFound(f"Message {message_id} not found")

        for key, value in payload.dict(exclude_unset=True).items():
            setattr(db_message, key, value)

        self.db.add(db_message)
        await self.db.commit()
        await self.db.refresh(db_message)
        return db_message

    async def delete_message(self, message_id: str):
        db_message = await self.get_message_by_id(message_id)
        if not db_message:
            raise NoResultFound(f"Message {message_id} not found")

        await self.db.delete(db_message)
        await self.db.commit()
        return {"deleted": True, "message_id": message_id}