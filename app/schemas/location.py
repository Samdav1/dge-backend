import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.user import LocationType


class LocationCreate(BaseModel):
    location_type: LocationType
    lat: float
    lon: float
    accuracy_meter: float


class LocationUpdate(BaseModel):
    location_type: LocationType | None = None
    lat: float | None = None
    lon: float | None = None
    accuracy_meter: float | None = None


class LocationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    location_type: LocationType
    lat: float
    lon: float
    accuracy_meter: float
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
# ✅ required for SQLModel → Pydantic conversion
