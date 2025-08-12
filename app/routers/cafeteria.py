from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
import logging
from bson import ObjectId
import hashlib
import json
from enum import Enum

from ..database import get_database
from ..schemas.cafeteria import (
    FoodItemCreate, FoodItemUpdate, FoodItem, MenuDayCreate, MenuDayUpdate, MenuDay,
    CafeteriaQRCode, QRCodeScanRequest, QRCodeScanResponse, CafeteriaStats,
    MealType, FoodCategory
)
from ..core.auth import get_current_active_user, get_current_user
from ..models.user import UserModel
from ..core.utils import format_datetime, format_object_id, validate_object_id
from ..core.exceptions import (
    CustomHTTPException, ValidationError, DatabaseError, 
    ResourceNotFoundError, ConflictError, AuthorizationError
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

class CafeteriaService:
    def __init__(self, db):
        self.db = db
    
    async def get_cafeterias(self, is_active: bool = True) -> List[Dict[str, Any]]:
        """Get all active cafeterias with basic information"""
        try:
            filter_query = {"is_active": is_active}
            
            cursor = self.db.cafeterias.find(filter_query).sort("name", 1)
            cafeterias = []
            
            async for cafeteria in cursor:
                cafeteria["_id"] = str(cafeteria["_id"])
                cafeterias.append(cafeteria)
            
            return cafeterias
            
        except Exception as e:
            logger.error(f"Error getting cafeterias: {str(e)}")
            raise DatabaseError("Failed to retrieve cafeterias", "get_cafeterias")
    
    async def get_cafeteria_menu(
        self, 
        cafeteria_id: str, 
        meal_type: Optional[str] = None,
        date_filter: Optional[date] = None,
        dietary_restrictions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get cafeteria menu with filtering options"""
        try:
            if not validate_object_id(cafeteria_id):
                raise ValidationError("Invalid cafeteria ID format", "cafeteria_id", cafeteria_id)
            
            # Check if cafeteria exists
            cafeteria = await self.db.cafeterias.find_one({"_id": ObjectId(cafeteria_id)})
            if not cafeteria:
                raise ResourceNotFoundError("Cafeteria", cafeteria_id)
            
            # Build menu filter
            menu_filter = {"cafeteria_id": ObjectId(cafeteria_id), "is_available": True}
            
            if meal_type:
                menu_filter["meal_type"] = meal_type
            
            if date_filter:
                # Convert date to datetime range for the day
                start_of_day = datetime.combine(date_filter, datetime.min.time())
                end_of_day = datetime.combine(date_filter, datetime.max.time())
                menu_filter["date"] = {"$gte": start_of_day, "$lte": end_of_day}
            
            # Get menu items
            cursor = self.db.menu_items.find(menu_filter).sort("category", 1)
            menu_items = []
            
            async for item in cursor:
                item["_id"] = str(item["_id"])
                item["cafeteria_id"] = str(item["cafeteria_id"])
                
                # Filter by dietary restrictions if specified
                if dietary_restrictions:
                    item_dietary = set(item.get("dietary_restrictions", []))
                    if not any(restriction in item_dietary for restriction in dietary_restrictions):
                        continue
                
                menu_items.append(item)
            
            # Group by category
            menu_by_category = {}
            for item in menu_items:
                category = item.get("category", "Other")
                if category not in menu_by_category:
                    menu_by_category[category] = []
                menu_by_category[category].append(item)
            
            return {
                "cafeteria": {
                    "id": str(cafeteria["_id"]),
                    "name": cafeteria["name"],
                    "location": cafeteria["location"],
                    "operating_hours": cafeteria.get("operating_hours", {}),
                    "contact": cafeteria.get("contact", {})
                },
                "menu": menu_by_category,
                "filters": {
                    "meal_type": meal_type,
                    "date": date_filter.isoformat() if date_filter else None,
                    "dietary_restrictions": dietary_restrictions
                },
                "total_items": len(menu_items)
            }
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting cafeteria menu: {str(e)}")
            raise DatabaseError("Failed to retrieve cafeteria menu", "get_cafeteria_menu")
    
    async def get_menu_categories(self) -> List[Dict[str, Any]]:
        """Get all available menu categories with item counts"""
        try:
            pipeline = [
                {"$match": {"is_available": True}},
                {
                    "$group": {
                        "_id": "$category",
                        "count": {"$sum": 1},
                        "avg_price": {"$avg": "$price"}
                    }
                },
                {"$sort": {"_id": 1}}
            ]
            
            categories = await self.db.menu_items.aggregate(pipeline).to_list(None)
            
            # Format response
            formatted_categories = []
            for cat in categories:
                formatted_categories.append({
                    "name": cat["_id"],
                    "item_count": cat["count"],
                    "average_price": round(cat["avg_price"], 2) if cat["avg_price"] else 0
                })
            
            return formatted_categories
            
        except Exception as e:
            logger.error(f"Error getting menu categories: {str(e)}")
            raise DatabaseError("Failed to retrieve menu categories", "get_menu_categories")
    
    async def search_menu(
        self,
        query: str,
        cafeteria_id: Optional[str] = None,
        max_price: Optional[float] = None,
        dietary_restrictions: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search menu items with comprehensive filtering"""
        try:
            if not query or len(query.strip()) < 2:
                raise ValidationError("Search query must be at least 2 characters long")
            
            # Build search filter
            search_filter = {
                "is_available": True,
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"description": {"$regex": query, "$options": "i"}},
                    {"ingredients": {"$regex": query, "$options": "i"}},
                    {"category": {"$regex": query, "$options": "i"}}
                ]
            }
            
            if cafeteria_id:
                if not validate_object_id(cafeteria_id):
                    raise ValidationError("Invalid cafeteria ID format", "cafeteria_id", cafeteria_id)
                search_filter["cafeteria_id"] = ObjectId(cafeteria_id)
            
            if max_price is not None:
                search_filter["price"] = {"$lte": max_price}
            
            if dietary_restrictions:
                search_filter["dietary_restrictions"] = {"$in": dietary_restrictions}
            
            # Get total count
            total_count = await self.db.menu_items.count_documents(search_filter)
            
            # Get search results with pagination
            cursor = self.db.menu_items.find(search_filter).sort("name", 1).skip(skip).limit(limit)
            results = []
            
            async for item in cursor:
                item["_id"] = str(item["_id"])
                item["cafeteria_id"] = str(item["cafeteria_id"])
                results.append(item)
            
            return {
                "query": query,
                "total_count": total_count,
                "results": results,
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "has_more": skip + limit < total_count
                },
                "filters": {
                    "cafeteria_id": cafeteria_id,
                    "max_price": max_price,
                    "dietary_restrictions": dietary_restrictions
                }
            }
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error searching menu: {str(e)}")
            raise DatabaseError("Failed to search menu", "search_menu")
    
    async def get_vegetarian_menu(
        self,
        cafeteria_id: Optional[str] = None,
        date_filter: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get vegetarian menu items"""
        try:
            # Build filter for vegetarian items
            filter_query = {
                "is_available": True,
                "dietary_restrictions": {"$in": ["vegetarian", "vegan"]}
            }
            
            if cafeteria_id:
                if not validate_object_id(cafeteria_id):
                    raise ValidationError("Invalid cafeteria ID format", "cafeteria_id", cafeteria_id)
                filter_query["cafeteria_id"] = ObjectId(cafeteria_id)
            
            if date_filter:
                start_of_day = datetime.combine(date_filter, datetime.min.time())
                end_of_day = datetime.combine(date_filter, datetime.max.time())
                filter_query["date"] = {"$gte": start_of_day, "$lte": end_of_day}
            
            # Get vegetarian items
            cursor = self.db.menu_items.find(filter_query).sort("category", 1)
            items = []
            
            async for item in cursor:
                item["_id"] = str(item["_id"])
                item["cafeteria_id"] = str(item["cafeteria_id"])
                items.append(item)
            
            # Group by cafeteria if no specific cafeteria specified
            if not cafeteria_id:
                items_by_cafeteria = {}
                for item in items:
                    cafeteria_name = item.get("cafeteria_name", "Unknown")
                    if cafeteria_name not in items_by_cafeteria:
                        items_by_cafeteria[cafeteria_name] = []
                    items_by_cafeteria[cafeteria_name].append(item)
                
                return {
                    "menu_type": "vegetarian",
                    "items_by_cafeteria": items_by_cafeteria,
                    "total_items": len(items),
                    "date": date_filter.isoformat() if date_filter else None
                }
            else:
                return {
                    "menu_type": "vegetarian",
                    "items": items,
                    "total_items": len(items),
                    "date": date_filter.isoformat() if date_filter else None
                }
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting vegetarian menu: {str(e)}")
            raise DatabaseError("Failed to retrieve vegetarian menu", "get_vegetarian_menu")
    
    async def get_halal_menu(
        self,
        cafeteria_id: Optional[str] = None,
        date_filter: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get halal menu items"""
        try:
            # Build filter for halal items
            filter_query = {
                "is_available": True,
                "dietary_restrictions": {"$in": ["halal"]}
            }
            
            if cafeteria_id:
                if not validate_object_id(cafeteria_id):
                    raise ValidationError("Invalid cafeteria ID format", "cafeteria_id", cafeteria_id)
                filter_query["cafeteria_id"] = ObjectId(cafeteria_id)
            
            if date_filter:
                start_of_day = datetime.combine(date_filter, datetime.min.time())
                end_of_day = datetime.combine(date_filter, datetime.max.time())
                filter_query["date"] = {"$gte": start_of_day, "$lte": end_of_day}
            
            # Get halal items
            cursor = self.db.menu_items.find(filter_query).sort("category", 1)
            items = []
            
            async for item in cursor:
                item["_id"] = str(item["_id"])
                item["cafeteria_id"] = str(item["cafeteria_id"])
                items.append(item)
            
            # Group by cafeteria if no specific cafeteria specified
            if not cafeteria_id:
                items_by_cafeteria = {}
                for item in items:
                    cafeteria_name = item.get("cafeteria_name", "Unknown")
                    if cafeteria_name not in items_by_cafeteria:
                        items_by_cafeteria[cafeteria_name] = []
                    items_by_cafeteria[cafeteria_name].append(item)
                
                return {
                    "menu_type": "halal",
                    "items_by_cafeteria": items_by_cafeteria,
                    "total_items": len(items),
                    "date": date_filter.isoformat() if date_filter else None
                }
            else:
                return {
                    "menu_type": "halal",
                    "items": items,
                    "total_items": len(items),
                    "date": date_filter.isoformat() if date_filter else None
                }
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting halal menu: {str(e)}")
            raise DatabaseError("Failed to retrieve halal menu", "get_halal_menu")
    
    async def get_todays_special(self, cafeteria_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get today's special menu items"""
        try:
            today = date.today()
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = datetime.combine(today, datetime.max.time())
            
            filter_query = {
                "is_available": True,
                "is_special": True,
                "date": {"$gte": start_of_day, "$lte": end_of_day}
            }
            
            if cafeteria_id:
                if not validate_object_id(cafeteria_id):
                    raise ValidationError("Invalid cafeteria ID format", "cafeteria_id", cafeteria_id)
                filter_query["cafeteria_id"] = ObjectId(cafeteria_id)
            
            # Get special items
            cursor = self.db.menu_items.find(filter_query).sort("price", 1)
            special_items = []
            
            async for item in cursor:
                item["_id"] = str(item["_id"])
                item["cafeteria_id"] = str(item["cafeteria_id"])
                special_items.append(item)
            
            return special_items
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting today's special: {str(e)}")
            raise DatabaseError("Failed to retrieve today's special", "get_todays_special")
    
    async def get_cafeteria_stats(self, cafeteria_id: str) -> Dict[str, Any]:
        """Get comprehensive cafeteria statistics"""
        try:
            if not validate_object_id(cafeteria_id):
                raise ValidationError("Invalid cafeteria ID format", "cafeteria_id", cafeteria_id)
            
            # Check if cafeteria exists
            cafeteria = await self.db.cafeterias.find_one({"_id": ObjectId(cafeteria_id)})
            if not cafeteria:
                raise ResourceNotFoundError("Cafeteria", cafeteria_id)
            
            # Get menu item statistics
            menu_stats = await self.db.menu_items.aggregate([
                {"$match": {"cafeteria_id": ObjectId(cafeteria_id)}},
                {
                    "$group": {
                        "_id": None,
                        "total_items": {"$sum": 1},
                        "available_items": {"$sum": {"$cond": ["$is_available", 1, 0]}},
                        "avg_price": {"$avg": "$price"},
                        "categories": {"$addToSet": "$category"},
                        "dietary_options": {"$addToSet": "$dietary_restrictions"}
                    }
                }
            ]).to_list(1)
            
            stats = menu_stats[0] if menu_stats else {
                "total_items": 0,
                "available_items": 0,
                "avg_price": 0,
                "categories": [],
                "dietary_options": []
            }
            
            # Flatten dietary options
            all_dietary = []
            for dietary_list in stats["dietary_options"]:
                if isinstance(dietary_list, list):
                    all_dietary.extend(dietary_list)
                else:
                    all_dietary.append(dietary_list)
            
            # Remove duplicates
            unique_dietary = list(set(all_dietary))
            
            return {
                "cafeteria_id": cafeteria_id,
                "cafeteria_name": cafeteria["name"],
                "menu_statistics": {
                    "total_items": stats["total_items"],
                    "available_items": stats["available_items"],
                    "average_price": round(stats["avg_price"], 2) if stats["avg_price"] else 0,
                    "categories": stats["categories"],
                    "dietary_options": unique_dietary
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting cafeteria stats: {str(e)}")
            raise DatabaseError("Failed to retrieve cafeteria statistics", "get_cafeteria_stats")

# API Endpoints
@router.get("/cafeterias", response_model=List[Dict[str, Any]])
async def get_cafeterias(
    active_only: bool = Query(True, description="Show only active cafeterias")
):
    """Get all cafeterias with basic information"""
    try:
        db = get_database()
        service = CafeteriaService(db)
        
        result = await service.get_cafeterias(is_active=active_only)
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_cafeterias endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/cafeterias/{cafeteria_id}/menu", response_model=Dict[str, Any])
async def get_cafeteria_menu(
    cafeteria_id: str,
    meal_type: Optional[str] = Query(None, description="Filter by meal type (breakfast, lunch, dinner, snacks)"),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    dietary: Optional[str] = Query(None, description="Filter by dietary restrictions (comma-separated)")
):
    """Get cafeteria menu with comprehensive filtering options"""
    try:
        # Parse date
        date_filter = None
        if date:
            try:
                date_filter = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Invalid date format. Use YYYY-MM-DD", "date", date)
        
        # Parse dietary restrictions
        dietary_restrictions = None
        if dietary:
            dietary_restrictions = [d.strip() for d in dietary.split(",")]
        
        db = get_database()
        service = CafeteriaService(db)
        
        result = await service.get_cafeteria_menu(
            cafeteria_id, meal_type, date_filter, dietary_restrictions
        )
        return result
        
    except (CustomHTTPException, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error in get_cafeteria_menu endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/menu/categories", response_model=List[Dict[str, Any]])
async def get_menu_categories():
    """Get all available menu categories with item counts and average prices"""
    try:
        db = get_database()
        service = CafeteriaService(db)
        
        result = await service.get_menu_categories()
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_menu_categories endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/menu/search", response_model=Dict[str, Any])
async def search_menu(
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    cafeteria_id: Optional[str] = Query(None, description="Filter by cafeteria ID"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    dietary: Optional[str] = Query(None, description="Dietary restrictions (comma-separated)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return")
):
    """Search menu items with comprehensive filtering and pagination"""
    try:
        # Parse dietary restrictions
        dietary_restrictions = None
        if dietary:
            dietary_restrictions = [d.strip() for d in dietary.split(",")]
        
        db = get_database()
        service = CafeteriaService(db)
        
        result = await service.search_menu(
            q, cafeteria_id, max_price, dietary_restrictions, skip, limit
        )
        return result
        
    except (CustomHTTPException, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error in search_menu endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/menu/vegetarian", response_model=Dict[str, Any])
async def get_vegetarian_menu(
    cafeteria_id: Optional[str] = Query(None, description="Filter by cafeteria ID"),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)")
):
    """Get vegetarian menu items with optional filtering"""
    try:
        # Parse date
        date_filter = None
        if date:
            try:
                date_filter = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Invalid date format. Use YYYY-MM-DD", "date", date)
        
        db = get_database()
        service = CafeteriaService(db)
        
        result = await service.get_vegetarian_menu(cafeteria_id, date_filter)
        return result
        
    except (CustomHTTPException, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error in get_vegetarian_menu endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/menu/halal", response_model=Dict[str, Any])
async def get_halal_menu(
    cafeteria_id: Optional[str] = Query(None, description="Filter by cafeteria ID"),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)")
):
    """Get halal menu items with optional filtering"""
    try:
        # Parse date
        date_filter = None
        if date:
            try:
                date_filter = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Invalid date format. Use YYYY-MM-DD", "date", date)
        
        db = get_database()
        service = CafeteriaService(db)
        
        result = await service.get_halal_menu(cafeteria_id, date_filter)
        return result
        
    except (CustomHTTPException, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error in get_halal_menu endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/menu/todays-special", response_model=List[Dict[str, Any]])
async def get_todays_special(
    cafeteria_id: Optional[str] = Query(None, description="Filter by cafeteria ID")
):
    """Get today's special menu items"""
    try:
        db = get_database()
        service = CafeteriaService(db)
        
        result = await service.get_todays_special(cafeteria_id)
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_todays_special endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/cafeterias/{cafeteria_id}/stats", response_model=Dict[str, Any])
async def get_cafeteria_stats(
    cafeteria_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get comprehensive cafeteria statistics"""
    try:
        db = get_database()
        service = CafeteriaService(db)
        
        result = await service.get_cafeteria_stats(cafeteria_id)
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_cafeteria_stats endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 