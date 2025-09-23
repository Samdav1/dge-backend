import uuid
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from enum import Enum
from app.models.user import UserStatus


class TeamMembership(SQLModel, table=True):
    __tablename__ = "team_memberships"

    team_id: uuid.UUID = Field(foreign_key="teams.id", primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="teamusers.id", primary_key=True)
    joined_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class TeamUsers(SQLModel, table=True):
    __tablename__ = "teamusers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(nullable=False, unique=True, index=True)
    password_hash: str = Field(nullable=False)
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_superuser: bool = Field(default=False, nullable=False)
    status: UserStatus = Field(default=UserStatus.active, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    teams: List["Teams"] = Relationship(
        back_populates="users", link_model=TeamMembership
    )
    permissions: List["Permissions"] = Relationship(back_populates="team_user")
    role: "Role" = Relationship(back_populates="team_user")
    assigned_tickets: list["SupportTicket"] = Relationship(back_populates="assigned_team_user")
    ticket_replies: list["SupportTicketReply"] = Relationship(back_populates="author_team_user")


class TeamType(str, Enum):
    customer_service = "customer_service"
    operations = "operations"
    finance = "finance"
    admin = "admin"
    technical = "technical"


class Teams(SQLModel, table=True):
    __tablename__ = "teams"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, unique=True, index=True)
    description: str | None = Field(default=None)
    team_type: TeamType = Field(
        default=TeamType.customer_service, nullable=False
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    users: List[TeamUsers] = Relationship(
        back_populates="teams", link_model=TeamMembership
    )


