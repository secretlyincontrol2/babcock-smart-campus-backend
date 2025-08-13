from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import logging
import asyncio
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo.errors import PyMongoError

from ..database import get_database
from ..core.auth import get_current_active_user
from ..core.exceptions import (
    CustomHTTPException, ValidationError, DatabaseError, 
    ResourceNotFoundError, AuthorizationError, RateLimitError
)
from ..models.user import UserModel
from ..schemas.maps import (
    LocationCreate, LocationResponse, LocationUpdate,
    DirectionsRequest, DirectionsResponse, NearbyRequest, NearbyResponse,
    CampusInfoResponse, LocationCategory
)

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

class MapsService:
    """Service class for maps-related business logic"""
    
    def __init__(self, db):
        self.db = db
        self.locations_collection = db.locations
        self.directions_cache = {}  # Simple in-memory cache for directions
    
    async def create_location(self, location_data: LocationCreate, created_by: str) -> LocationResponse:
        """Create a new location"""
        try:
            # Validate coordinates
            if not (-90 <= location_data.latitude <= 90):
                raise ValidationError("Latitude must be between -90 and 90 degrees")
            if not (-180 <= location_data.longitude <= 180):
                raise ValidationError("Longitude must be between -180 and 180 degrees")
            
            # Check if location already exists at these coordinates
            existing_location = await self.locations_collection.find_one({
                "latitude": location_data.latitude,
                "longitude": location_data.longitude,
                "is_active": True
            })
            
            if existing_location:
                raise ValidationError("A location already exists at these coordinates")
            
            location_doc = {
                **location_data.dict(),
                "created_by": ObjectId(created_by),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True,
                "visit_count": 0,
                "rating": 0.0,
                "total_ratings": 0
            }
            
            result = await self.locations_collection.insert_one(location_doc)
            location_doc["_id"] = result.inserted_id
            
            logger.info(f"Location created: {location_doc['name']} by user {created_by}")
            return LocationResponse(**location_doc)
            
        except PyMongoError as e:
            logger.error(f"Database error in create_location: {str(e)}")
            raise DatabaseError("Failed to create location due to database error")
        except Exception as e:
            logger.error(f"Unexpected error in create_location: {str(e)}")
            raise DatabaseError("Failed to create location due to an unexpected error")
    
    async def get_locations(
        self, 
        category: Optional[LocationCategory] = None,
        limit: int = Query(50, ge=1, le=100),
        skip: int = Query(0, ge=0),
        search: Optional[str] = None
    ) -> List[LocationResponse]:
        """Get locations with optional filtering and pagination"""
        try:
            # Build filter
            filter_query = {"is_active": True}
            
            if category:
                filter_query["category"] = category.value
            
            if search:
                filter_query["$or"] = [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}},
                    {"tags": {"$in": [search]}}
                ]
            
            # Execute query with pagination
            cursor = self.locations_collection.find(filter_query)
            cursor = cursor.skip(skip).limit(limit).sort("name", 1)
            
            locations = []
            async for doc in cursor:
                locations.append(LocationResponse(**doc))
            
            logger.info(f"Retrieved {len(locations)} locations")
            return locations
            
        except PyMongoError as e:
            logger.error(f"Database error in get_locations: {str(e)}")
            raise DatabaseError("Failed to retrieve locations due to database error")
        except Exception as e:
            logger.error(f"Unexpected error in get_locations: {str(e)}")
            raise DatabaseError("Failed to retrieve locations due to an unexpected error")
    
    async def get_location_by_id(self, location_id: str) -> LocationResponse:
        """Get a specific location by ID"""
        try:
            if not ObjectId.is_valid(location_id):
                raise ValidationError("Invalid location ID format")
            
            location_doc = await self.locations_collection.find_one({
                "_id": ObjectId(location_id),
                "is_active": True
            })
            
            if not location_doc:
                raise ResourceNotFoundError("Location not found")
            
            # Increment visit count
            await self.locations_collection.update_one(
                {"_id": ObjectId(location_id)},
                {"$inc": {"visit_count": 1}}
            )
            
            logger.info(f"Location retrieved: {location_doc['name']}")
            return LocationResponse(**location_doc)
            
        except PyMongoError as e:
            logger.error(f"Database error in get_location_by_id: {str(e)}")
            raise DatabaseError("Failed to retrieve location due to database error")
        except Exception as e:
            logger.error(f"Unexpected error in get_location_by_id: {str(e)}")
            raise DatabaseError("Failed to retrieve location due to an unexpected error")
    
    async def update_location(
        self, 
        location_id: str, 
        location_data: LocationUpdate, 
        updated_by: str
    ) -> LocationResponse:
        """Update an existing location"""
        try:
            if not ObjectId.is_valid(location_id):
                raise ValidationError("Invalid location ID format")
            
            # Check if location exists
            existing_location = await self.locations_collection.find_one({
                "_id": ObjectId(location_id),
                "is_active": True
            })
            
            if not existing_location:
                raise ResourceNotFoundError("Location not found")
            
            # Check permissions (only creator or admin can update)
            if str(existing_location["created_by"]) != updated_by:
                # Check if user is admin
                user = await self.db.users.find_one({"_id": ObjectId(updated_by)})
                if not user or user.get("role") != "admin":
                    raise AuthorizationError("Insufficient privileges to update this location")
            
            # Validate coordinates if they're being updated
            if location_data.latitude is not None:
                if not (-90 <= location_data.latitude <= 90):
                    raise ValidationError("Latitude must be between -90 and 90 degrees")
            
            if location_data.longitude is not None:
                if not (-180 <= location_data.longitude <= 180):
                    raise ValidationError("Longitude must be between -180 and 180 degrees")
            
            # Prepare update data
            update_data = location_data.dict(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow()
            update_data["updated_by"] = ObjectId(updated_by)
            
            # Update location
            result = await self.locations_collection.update_one(
                {"_id": ObjectId(location_id)},
                {"$set": update_data}
            )
            
            if result.modified_count == 0:
                raise DatabaseError("No changes were made to the location")
            
            # Get updated location
            updated_location = await self.get_location_by_id(location_id)
            
            logger.info(f"Location updated: {updated_location.name} by user {updated_by}")
            return updated_location
            
        except PyMongoError as e:
            logger.error(f"Database error in update_location: {str(e)}")
            raise DatabaseError("Failed to update location due to database error")
        except Exception as e:
            logger.error(f"Unexpected error in update_location: {str(e)}")
            raise DatabaseError("Failed to update location due to an unexpected error")
    
    async def delete_location(self, location_id: str, deleted_by: str) -> bool:
        """Soft delete a location"""
        try:
            if not ObjectId.is_valid(location_id):
                raise ValidationError("Invalid location ID format")
            
            # Check if location exists
            existing_location = await self.locations_collection.find_one({
                "_id": ObjectId(location_id),
                "is_active": True
            })
            
            if not existing_location:
                raise ResourceNotFoundError("Location not found")
            
            # Check permissions (only creator or admin can delete)
            if str(existing_location["created_by"]) != deleted_by:
                # Check if user is admin
                user = await self.db.users.find_one({"_id": ObjectId(deleted_by)})
                if not user or user.get("role") != "admin":
                    raise AuthorizationError("Insufficient privileges to delete this location")
            
            # Soft delete
            result = await self.locations_collection.update_one(
                {"_id": ObjectId(location_id)},
                {
                    "$set": {
                        "is_active": False,
                        "deleted_at": datetime.utcnow(),
                        "deleted_by": ObjectId(deleted_by)
                    }
                }
            )
            
            if result.modified_count == 0:
                raise DatabaseError("Failed to delete location")
            
            logger.info(f"Location deleted: {existing_location['name']} by user {deleted_by}")
            return True
            
        except PyMongoError as e:
            logger.error(f"Database error in delete_location: {str(e)}")
            raise DatabaseError("Failed to delete location due to database error")
        except Exception as e:
            logger.error(f"Unexpected error in delete_location: {str(e)}")
            raise DatabaseError("Failed to delete location due to an unexpected error")
    
    async def get_nearby_locations(
        self, 
        latitude: float, 
        longitude: float, 
        radius: float = 1000,
        category: Optional[LocationCategory] = None,
        limit: int = 20
    ) -> NearbyResponse:
        """Get locations within a specified radius"""
        try:
            # Validate coordinates
            if not (-90 <= latitude <= 90):
                raise ValidationError("Latitude must be between -90 and 90 degrees")
            if not (-180 <= longitude <= 180):
                raise ValidationError("Longitude must be between -180 and 180 degrees")
            if radius <= 0:
                raise ValidationError("Radius must be positive")
            
            # Build filter
            filter_query = {
                "is_active": True,
                "latitude": {"$gte": latitude - (radius / 111000), "$lte": latitude + (radius / 111000)},
                "longitude": {"$gte": longitude - (radius / (111000 * abs(latitude))), "$lte": longitude + (radius / (111000 * abs(latitude)))}
            }
            
            if category:
                filter_query["category"] = category.value
            
            # Execute query
            cursor = self.locations_collection.find(filter_query)
            cursor = cursor.limit(limit).sort("visit_count", -1)
            
            locations = []
            async for doc in cursor:
                # Calculate actual distance
                distance = self._calculate_distance(
                    latitude, longitude, 
                    doc["latitude"], doc["longitude"]
                )
                
                if distance <= radius:
                    location_data = LocationResponse(**doc)
                    locations.append({
                        "location": location_data,
                        "distance": round(distance, 2)
                    })
            
            # Sort by distance
            locations.sort(key=lambda x: x["distance"])
            
            logger.info(f"Found {len(locations)} nearby locations within {radius}m")
            return NearbyResponse(
                locations=locations,
                center_lat=latitude,
                center_lng=longitude,
                radius=radius,
                total_found=len(locations)
            )
            
        except PyMongoError as e:
            logger.error(f"Database error in get_nearby_locations: {str(e)}")
            raise DatabaseError("Failed to retrieve nearby locations due to database error")
        except Exception as e:
            logger.error(f"Unexpected error in get_nearby_locations: {str(e)}")
            raise DatabaseError("Failed to retrieve nearby locations due to an unexpected error")
    
    async def get_directions(
        self, 
        origin_lat: float, 
        origin_lng: float, 
        dest_lat: float, 
        dest_lng: float,
        mode: str = "walking"
    ) -> DirectionsResponse:
        """Get directions between two points"""
        try:
            # Validate coordinates
            for lat, lng, name in [(origin_lat, origin_lng, "origin"), (dest_lat, dest_lng, "destination")]:
                if not (-90 <= lat <= 90):
                    raise ValidationError(f"{name.capitalize()} latitude must be between -90 and 90 degrees")
                if not (-180 <= lng <= 180):
                    raise ValidationError(f"{name.capitalize()} longitude must be between -180 and 180 degrees")
            
            # Validate mode
            valid_modes = ["walking", "driving", "bicycling", "transit"]
            if mode not in valid_modes:
                raise ValidationError(f"Mode must be one of: {', '.join(valid_modes)}")
            
            # Check cache first
            cache_key = f"{origin_lat},{origin_lng}_{dest_lat},{dest_lng}_{mode}"
            if cache_key in self.directions_cache:
                cached_result = self.directions_cache[cache_key]
                if datetime.utcnow() - cached_result["cached_at"] < timedelta(hours=1):
                    logger.info("Returning cached directions")
                    return cached_result["data"]
            
            # Calculate distance and estimated time
            distance = self._calculate_distance(origin_lat, origin_lng, dest_lat, dest_lng)
            
            # Estimate travel time based on mode
            travel_time = self._estimate_travel_time(distance, mode)
            
            # Create directions response
            directions = DirectionsResponse(
                origin={"lat": origin_lat, "lng": origin_lng},
                destination={"lat": dest_lat, "lng": dest_lng},
                distance=distance,
                duration=travel_time,
                mode=mode,
                steps=[
                    {
                        "instruction": f"Start at coordinates ({origin_lat}, {origin_lng})",
                        "distance": 0,
                        "duration": 0
                    },
                    {
                        "instruction": f"Travel {mode} to coordinates ({dest_lat}, {dest_lng})",
                        "distance": distance,
                        "duration": travel_time
                    }
                ]
            )
            
            # Cache the result
            self.directions_cache[cache_key] = {
                "data": directions,
                "cached_at": datetime.utcnow()
            }
            
            logger.info(f"Generated directions: {distance:.2f}m, {travel_time:.0f}min, mode: {mode}")
            return directions
            
        except Exception as e:
            logger.error(f"Error in get_directions: {str(e)}")
            raise DatabaseError("Failed to generate directions")
    
    async def get_campus_info(self) -> CampusInfoResponse:
        """Get general campus information and statistics"""
        try:
            # Get location statistics
            total_locations = await self.locations_collection.count_documents({"is_active": True})
            
            # Get locations by category
            pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {"_id": "$category", "count": {"$sum": 1}}}
            ]
            
            category_stats = []
            async for result in self.locations_collection.aggregate(pipeline):
                category_stats.append({
                    "category": result["_id"],
                    "count": result["count"]
                })
            
            # Get most visited locations
            most_visited = []
            cursor = self.locations_collection.find({"is_active": True})
            cursor = cursor.sort("visit_count", -1).limit(5)
            
            async for doc in cursor:
                most_visited.append({
                    "name": doc["name"],
                    "visit_count": doc["visit_count"],
                    "category": doc["category"]
                })
            
            campus_info = CampusInfoResponse(
                total_locations=total_locations,
                category_stats=category_stats,
                most_visited_locations=most_visited,
                last_updated=datetime.utcnow()
            )
            
            logger.info(f"Retrieved campus info: {total_locations} locations")
            return campus_info
            
        except PyMongoError as e:
            logger.error(f"Database error in get_campus_info: {str(e)}")
            raise DatabaseError("Failed to retrieve campus information due to database error")
        except Exception as e:
            logger.error(f"Unexpected error in get_campus_info: {str(e)}")
            raise DatabaseError("Failed to retrieve campus information due to an unexpected error")
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        import math
        
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _estimate_travel_time(self, distance: float, mode: str) -> int:
        """Estimate travel time in minutes based on distance and mode"""
        # Average speeds in m/s
        speeds = {
            "walking": 1.4,      # 5 km/h
            "bicycling": 4.2,    # 15 km/h
            "driving": 13.9,     # 50 km/h
            "transit": 8.3       # 30 km/h
        }
        
        speed = speeds.get(mode, 1.4)
        time_seconds = distance / speed
        return int(time_seconds / 60)  # Convert to minutes

# Rate limiting cache (simple in-memory implementation)
request_cache = {}

def check_rate_limit(user_id: str, endpoint: str, max_requests: int = 100, window_minutes: int = 1):
    """Simple rate limiting implementation"""
    current_time = datetime.utcnow()
    cache_key = f"{user_id}_{endpoint}"
    
    if cache_key in request_cache:
        requests = request_cache[cache_key]
        # Remove old requests outside the time window
        requests = [req for req in requests if current_time - req < timedelta(minutes=window_minutes)]
        
        if len(requests) >= max_requests:
            raise RateLimitError(f"Rate limit exceeded: {max_requests} requests per {window_minutes} minute(s)")
        
        requests.append(current_time)
        request_cache[cache_key] = requests
    else:
        request_cache[cache_key] = [current_time]

@router.get("/locations", response_model=List[LocationResponse], status_code=status.HTTP_200_OK)
async def get_locations(
    category: Optional[LocationCategory] = Query(None, description="Filter by location category"),
    limit: int = Query(50, ge=1, le=100, description="Number of locations to return"),
    skip: int = Query(0, ge=0, description="Number of locations to skip"),
    search: Optional[str] = Query(None, description="Search term for location names and descriptions"),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get locations with optional filtering and pagination.
    Requires authentication.
    """
    try:
        # Rate limiting
        check_rate_limit(str(current_user._id), "get_locations")
        
        db = await get_database()
        service = MapsService(db)
        
        locations = await service.get_locations(
            category=category,
            limit=limit,
            skip=skip,
            search=search
        )
        
        return locations
        
    except CustomHTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled error in get_locations: {str(e)}")
        raise DatabaseError("Failed to retrieve locations due to an unexpected error")

@router.get("/locations/{location_id}", response_model=LocationResponse, status_code=status.HTTP_200_OK)
async def get_location_by_id(
    location_id: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get a specific location by ID.
    Requires authentication.
    """
    try:
        # Rate limiting
        check_rate_limit(str(current_user._id), "get_location_by_id")
        
        db = await get_database()
        service = MapsService(db)
        
        location = await service.get_location_by_id(location_id)
        return location
        
    except CustomHTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled error in get_location_by_id: {str(e)}")
        raise DatabaseError("Failed to retrieve location due to an unexpected error")

@router.post("/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    location_data: LocationCreate,
    current_user: UserModel = Depends(get_current_active_user),
    background_tasks: BackgroundTasks = None
):
    """
    Create a new location.
    Requires: User or Admin role.
    """
    try:
        # Rate limiting
        check_rate_limit(str(current_user._id), "create_location", max_requests=10, window_minutes=5)
        
        # Check permissions
        if current_user.role not in ["user", "admin"]:
            raise AuthorizationError("Insufficient privileges to create locations")
        
        db = await get_database()
        service = MapsService(db)
        
        new_location = await service.create_location(location_data, str(current_user._id))
        
        # Background task: Notify relevant users about new location
        if background_tasks:
            background_tasks.add_task(notify_users_new_location, new_location.category)
        
        return new_location
        
    except CustomHTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled error in create_location: {str(e)}")
        raise DatabaseError("Failed to create location due to an unexpected error")

@router.put("/locations/{location_id}", response_model=LocationResponse, status_code=status.HTTP_200_OK)
async def update_location(
    location_id: str,
    location_data: LocationUpdate,
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Update an existing location.
    Requires: Location creator or Admin role.
    """
    try:
        # Rate limiting
        check_rate_limit(str(current_user._id), "update_location", max_requests=20, window_minutes=5)
        
        db = await get_database()
        service = MapsService(db)
        
        updated_location = await service.update_location(location_id, location_data, str(current_user._id))
        return updated_location
        
    except CustomHTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled error in update_location: {str(e)}")
        raise DatabaseError("Failed to update location due to an unexpected error")

@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Delete a location (soft delete).
    Requires: Location creator or Admin role.
    """
    try:
        # Rate limiting
        check_rate_limit(str(current_user._id), "delete_location", max_requests=5, window_minutes=5)
        
        db = await get_database()
        service = MapsService(db)
        
        await service.delete_location(location_id, str(current_user._id))
        return None
        
    except CustomHTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled error in delete_location: {str(e)}")
        raise DatabaseError("Failed to delete location due to an unexpected error")

@router.get("/nearby", response_model=NearbyResponse, status_code=status.HTTP_200_OK)
async def get_nearby_locations(
    latitude: float = Query(..., ge=-90, le=90, description="Center latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Center longitude"),
    radius: float = Query(1000, ge=100, le=10000, description="Search radius in meters"),
    category: Optional[LocationCategory] = Query(None, description="Filter by location category"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of locations to return"),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get locations within a specified radius.
    Requires authentication.
    """
    try:
        # Rate limiting
        check_rate_limit(str(current_user._id), "get_nearby_locations")
        
        db = await get_database()
        service = MapsService(db)
        
        nearby_locations = await service.get_nearby_locations(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            category=category,
            limit=limit
        )
        
        return nearby_locations
        
    except CustomHTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled error in get_nearby_locations: {str(e)}")
        raise DatabaseError("Failed to retrieve nearby locations due to an unexpected error")

@router.get("/directions", response_model=DirectionsResponse, status_code=status.HTTP_200_OK)
async def get_directions(
    origin_lat: float = Query(..., ge=-90, le=90, description="Origin latitude"),
    origin_lng: float = Query(..., ge=-180, le=180, description="Origin longitude"),
    dest_lat: float = Query(..., ge=-90, le=90, description="Destination latitude"),
    dest_lng: float = Query(..., ge=-180, le=180, description="Destination longitude"),
    mode: str = Query("walking", description="Travel mode: walking, driving, bicycling, transit"),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get directions between two points.
    Requires authentication.
    """
    try:
        # Rate limiting
        check_rate_limit(str(current_user._id), "get_directions")
        
        db = await get_database()
        service = MapsService(db)
        
        directions = await service.get_directions(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            mode=mode
        )
        
        return directions
        
    except CustomHTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled error in get_directions: {str(e)}")
        raise DatabaseError("Failed to generate directions due to an unexpected error")

@router.get("/campus-info", response_model=CampusInfoResponse, status_code=status.HTTP_200_OK)
async def get_campus_info(
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get general campus information and statistics.
    Requires authentication.
    """
    try:
        # Rate limiting
        check_rate_limit(str(current_user._id), "get_campus_info")
        
        db = await get_database()
        service = MapsService(db)
        
        campus_info = await service.get_campus_info()
        return campus_info
        
    except CustomHTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled error in get_campus_info: {str(e)}")
        raise DatabaseError("Failed to retrieve campus information due to an unexpected error")

# Background task functions
async def notify_users_new_location(category: str):
    """Background task to notify users about new locations"""
    try:
        logger.info(f"Notifying users about new {category} location")
        # Implementation would include:
        # - Finding users interested in this category
        # - Sending push notifications or emails
        # - Updating user feeds
        await asyncio.sleep(1)  # Simulate work
        logger.info(f"Successfully notified users about new {category} location")
    except Exception as e:
        logger.error(f"Failed to notify users about new location: {str(e)}") 