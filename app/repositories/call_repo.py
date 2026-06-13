
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.models.call import CallSession, CallParticipant, CallRecording


class CallRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, call: CallSession):
        self.db.add(call)

    async def get_session_by_id(self, session_id):
        result = await self.db.exec(select(CallSession).where(CallSession.id == session_id))
        return result.first()

    async def add_participant(self, participant: CallParticipant):
        self.db.add(participant)

    async def update_status(self, call_session: CallSession, status):
        call_session.status = status

    async def add_recording(self, recording: CallRecording):
        self.db.add(recording)
