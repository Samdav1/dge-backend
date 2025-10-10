# app/services/message_service.py
from app.repositories.messages_repo import MessageRepository
from app.schemas.messages import MessageCreate, MessageUpdate


class MessageService:
    def __init__(self, repo: MessageRepository):
        self.repo = repo

    async def create_message(self, payload: MessageCreate):
        return await self.repo.create_message(payload)

    async def get_conversation_messages(self, conversation_id: str):
        return await self.repo.get_messages_by_conversation(conversation_id)

    async def get_message(self, message_id: str):
        return await self.repo.get_message_by_id(message_id)

    async def update_message(self, message_id: str, payload: MessageUpdate):
        return await self.repo.update_message(message_id, payload)

    async def delete_message(self, message_id: str):
        return await self.repo.delete_message(message_id)