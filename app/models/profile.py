from sqlmodel import SQLModel, Field, Relationship
import uuid
from typing import Optional
from datetime import datetime, timezone, date



class Profile(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", unique=True, nullable=False, index=True)
    team_id: Optional[uuid.UUID] = Field(foreign_key="teamusers.id", nullable=False, index=True)
    first_name: str = Field(nullable=False, index=True)
    last_name: str = Field(nullable=False, index=True)
    date_of_birth: Optional[date] = None

    gender: Optional[str] = Field(default=None)
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = Field(nullable=False, index=True)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user: 'Users' = Relationship(back_populates='profile')
    team: 'TeamUsers' = Relationship(back_populates='profile')

    @property
    def age(self) -> Optional[int]:
        """Compute age dynamically from date_of_birth."""
        if not self.date_of_birth:
            return None
        today = date.today()
        return (
                today.year
                - self.date_of_birth.year
                - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )