from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LocationBase(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    building_code: Optional[str] = None
    floor_number: Optional[int] = None
    room_number: Optional[str] = None
    opening_hours: Optional[str] = None
    contact_number: Optional[str] = None
    image_url: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class LocationResponse(LocationBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True 