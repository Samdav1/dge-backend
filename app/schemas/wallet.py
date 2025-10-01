import uuid
from typing import Optional
from pydantic import BaseModel
from enum import Enum


class WalletType(str, Enum):
    deposit = "deposit"
    earnings = "earnings"

class WalletBase(BaseModel):
    wallet_type: WalletType
    balance_cents: float = 0.00
    currency: str = "NGN"

class WalletCreate(WalletBase):
    user_id: uuid.UUID

class WalletUpdate(BaseModel):
    wallet_type: Optional[WalletType] = None
    balance_cents: Optional[int] = None
    currency: Optional[str] = None

class WalletRead(WalletBase):
    id: uuid.UUID
    user_id: uuid.UUID

    class Config:
        from_attributes = True