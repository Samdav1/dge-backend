import secrets
import string
import uuid
from datetime import datetime, timezone
from typing import Optional, List
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

def generate_referral_code(length=8):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for i in range(length))

class Users(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(nullable=False, unique=True, index=True)
    password: str = Field(nullable=False)
    username: str = Field(nullable=False, unique=True, index=True)
    status: UserStatus = Field(default=UserStatus.active, nullable=False)
    referral_code: str = Field(
        default_factory=generate_referral_code,
        unique=True,
        index=True,
        nullable=False
    )
    referred_by_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    referrer: Optional["Users"] = Relationship(
        back_populates="referrals",
        sa_relationship_kwargs={"remote_side": "Users.id"}
    )
    referrals: List["Users"] = Relationship(back_populates="referrer")
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
    call_participations: "CallParticipant" = Relationship(back_populates="users")
    kyc: "KYC" = Relationship(back_populates="user")
    services : list["Service"] = Relationship(back_populates="user")
    negotiations_outgoing: list["PriceNegotiation"] = Relationship(
        back_populates="initiator",
        sa_relationship_kwargs={"foreign_keys": "[PriceNegotiation.initiator_id]"}
    )
    negotiations_incoming: list["PriceNegotiation"] = Relationship(
        back_populates="receiver",
        sa_relationship_kwargs={"foreign_keys": "[PriceNegotiation.receiver_id]"}
    )
    notifications: list["Notification"] = Relationship(back_populates="user")


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