from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from pydantic import BaseModel, Field

class LocationModel(BaseModel):
    """MongoDB model for locations"""
    
    # MongoDB fields
    _id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    
    # Location details
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    category: str = Field(..., description="Location category")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str = Field(..., min_length=1, max_length=200)
    
    # Building details
    building_code: Optional[str] = Field(None, max_length=20)
    floor: Optional[int] = Field(None, ge=0, le=100)
    room_number: Optional[str] = Field(None, max_length=20)
    
    # Additional info
    opening_hours: Optional[str] = Field(None, max_length=100)
    contact_info: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=255)
    tags: List[str] = Field(default_factory=list)
    
    # Status and metrics
    is_active: bool = Field(default=True)
    visit_count: int = Field(default=0, ge=0)
    rating: float = Field(default=0.0, ge=0.0, le=5.0)
    total_ratings: int = Field(default=0, ge=0)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by: ObjectId = Field(..., description="User ID who created this location")
    updated_by: Optional[ObjectId] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[ObjectId] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True

    def to_dict(self) -> dict:
        """Convert model to dictionary for MongoDB operations"""
        data = self.dict(exclude={"_id"})
        if self._id:
            data["_id"] = self._id
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "LocationModel":
        """Create model from dictionary"""
        if "_id" in data and isinstance(data["_id"], ObjectId):
            data["_id"] = str(data["_id"])
        return cls(**data)

# MongoDB collection name
LOCATIONS_COLLECTION = "locations" 