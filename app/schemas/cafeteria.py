from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CafeteriaBase(BaseModel):
    name: str
    location: str
    building: str
    latitude: float
    longitude: float
    opening_time: str
    closing_time: str
    description: Optional[str] = None
    image_url: Optional[str] = None

class CafeteriaCreate(CafeteriaBase):
    pass

class CafeteriaResponse(CafeteriaBase):
    id: int
    is_open: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class MenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category: str
    is_vegetarian: bool = False
    is_halal: bool = False
    image_url: Optional[str] = None
    preparation_time: Optional[int] = None
    calories: Optional[int] = None
    allergens: Optional[str] = None

class MenuItemCreate(MenuItemBase):
    cafeteria_id: int

class MenuItemResponse(MenuItemBase):
    id: int
    cafeteria_id: int
    is_available: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True 