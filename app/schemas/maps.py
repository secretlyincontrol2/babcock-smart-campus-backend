from pydantic import BaseModel, Field, field_validator
from typing import Optional, Annotated, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from enum import Enum

class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return handler(str)

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

class LocationCategory(str, Enum):
    ACADEMIC = "academic"
    ADMINISTRATIVE = "administrative"
    RECREATIONAL = "recreational"
    RESIDENTIAL = "residential"
    DINING = "dining"
    TRANSPORTATION = "transportation"
    HEALTH = "health"
    SECURITY = "security"
    PARKING = "parking"
    LIBRARY = "library"
    SPORTS = "sports"

class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    category: LocationCategory
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str = Field(..., min_length=1, max_length=200)
    building_code: Optional[str] = Field(None, max_length=20)
    floor: Optional[int] = Field(None, ge=0, le=100)
    room_number: Optional[str] = Field(None, max_length=20)
    opening_hours: Optional[str] = Field(None, max_length=100)
    contact_info: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = Field(default_factory=list)

class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    category: Optional[LocationCategory] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, min_length=1, max_length=200)
    building_code: Optional[str] = Field(None, max_length=20)
    floor: Optional[int] = Field(None, ge=0, le=100)
    room_number: Optional[str] = Field(None, max_length=20)
    opening_hours: Optional[str] = Field(None, max_length=100)
    contact_info: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None

class LocationResponse(BaseModel):
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    name: str
    description: str
    category: LocationCategory
    latitude: float
    longitude: float
    address: str
    building_code: Optional[str] = None
    floor: Optional[int] = None
    room_number: Optional[str] = None
    opening_hours: Optional[str] = None
    contact_info: Optional[str] = None
    image_url: Optional[str] = None
    tags: List[str] = []
    is_active: bool = True
    visit_count: int = 0
    rating: float = 0.0
    total_ratings: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: PyObjectId

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class DirectionsRequest(BaseModel):
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lng: float = Field(..., ge=-180, le=180)
    dest_lat: float = Field(..., ge=-90, le=90)
    dest_lng: float = Field(..., ge=-180, le=180)
    mode: str = Field("walking", pattern="^(walking|driving|bicycling|transit)$")

class DirectionsResponse(BaseModel):
    origin: Dict[str, float]
    destination: Dict[str, float]
    distance: float
    duration: int
    mode: str
    steps: List[Dict[str, Any]]

class NearbyRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius: float = Field(1000, ge=100, le=10000)
    category: Optional[LocationCategory] = None
    limit: int = Field(20, ge=1, le=50)

class NearbyResponse(BaseModel):
    locations: List[Dict[str, Any]]
    center_lat: float
    center_lng: float
    radius: float
    total_found: int

class CampusInfoResponse(BaseModel):
    total_locations: int
    category_stats: List[Dict[str, Any]]
    most_visited_locations: List[Dict[str, Any]]
    last_updated: datetime

# Legacy schemas for backward compatibility
class LocationType(str, Enum):
    ACADEMIC = "academic"
    ADMINISTRATIVE = "administrative"
    RECREATIONAL = "recreational"
    RESIDENTIAL = "residential"
    DINING = "dining"
    TRANSPORTATION = "transportation"
    HEALTH = "health"
    SECURITY = "security"
    PARKING = "parking"
    LIBRARY = "library"
    SPORTS = "sports"

class CampusLocation(BaseModel):
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    name: str
    description: str
    location_type: LocationType
    building_code: str
    floor: Optional[int] = None
    room_number: Optional[str] = None
    latitude: float
    longitude: float
    address: str
    is_active: bool = True
    opening_hours: Optional[str] = None
    contact_info: Optional[str] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class NavigationRequest(BaseModel):
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    mode: str = "walking"  # walking, driving, cycling
    avoid_traffic: bool = False

class NavigationResponse(BaseModel):
    route_exists: bool
    distance: float
    duration: int
    steps: List[dict]
    polyline: str
    warnings: List[str]

class NearbySearch(BaseModel):
    latitude: float
    longitude: float
    radius: float = 1000  # meters
    location_types: Optional[List[LocationType]] = None
    limit: int = 20

class LocationStats(BaseModel):
    total_locations: int
    locations_by_type: dict
    popular_locations: List[dict]
    recent_additions: List[dict] 