import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    banned = "banned"

class LocationType(str, Enum):
    CURRENT = "current"
    PERMANENT = "permanent"
    OFFICE = "office"
    HOME = "home"

class Users(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(nullable=False, unique=True, index=True)
    password: str = Field(nullable=False)
    username: str = Field(nullable=False, unique=True, index=True)
    status: UserStatus = Field(default=UserStatus.active, nullable=False)
    created_at: datetime = Field(default_factory= lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory= lambda: datetime.now(timezone.utc), nullable=False)
    locations: list["Locations"] = Relationship(back_populates="user")
    profile: 'Profile' = Relationship(back_populates='user')
    wallet : 'Wallet' = Relationship(back_populates='user')
    transactions: list["Transaction"] = Relationship(back_populates="user")
    portfolios: list["UserPortfolio"] = Relationship(back_populates="user")
    reviews: list["Review"] = Relationship(back_populates="user")
    support_tickets: list["SupportTicket"] = Relationship(back_populates="user")
    ticket_replies: list["SupportTicketReply"] = Relationship(back_populates="author_user")
    conversations: list["ConversationParticipant"] = Relationship(back_populates="user")
    messages: list["Message"] = Relationship(back_populates="sender")
    read_receipts: list['MessageReadReceipt'] = Relationship(back_populates="user")
    presence: "Presence" = Relationship(back_populates="user")
    initiated_calls: list["CallSession"] = Relationship(back_populates="initiator")


class Locations(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(nullable=False, foreign_key="users.id")
    location_type: LocationType = Field(nullable=False)
    lat: float = Field(nullable=False)
    lon: float = Field(nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    accuracy_meter: float = Field(nullable=False)
    user: Users = Relationship(back_populates="locations")

class Admin(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    profile_id: uuid.UUID = Field(nullable=False, foreign_key="profile.id")
    team_id: Optional[uuid.UUID]= Field( foreign_key="teams.id")
    full_permission: bool = Field(default=True, nullable=False)
    team: Optional['Teams']= Relationship(back_populates="admin")