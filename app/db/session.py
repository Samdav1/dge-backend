from sqlmodel import SQLModel, create_engine, Session

from app.config import settings

engine = create_engine(settings.database_uri, echo=True)

def get_session():
    with Session(engine) as session:
        yield session