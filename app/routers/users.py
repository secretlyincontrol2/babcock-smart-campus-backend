from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from bson import ObjectId
import hashlib
import secrets
import json

from ..database import get_database
from ..schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserLogin, AdminCreate, AdminUpdate,
    UserRole, UserStatus
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

class UserService:
    def __init__(self, db):
        self.db = db
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get detailed user profile with statistics"""
        try:
            if not validate_object_id(user_id):
                raise ValidationError("Invalid user ID format", "user_id", user_id)
            
            user_data = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user_data:
                raise ResourceNotFoundError("User", user_id)
            
            # Get user statistics
            stats = await self._get_user_stats(user_id)
            
            # Format user data
            user_data["_id"] = str(user_data["_id"])
            user_data["stats"] = stats
            
            return user_data
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            raise DatabaseError("Failed to retrieve user profile", "get_user_profile")
    
    async def update_user_profile(
        self, 
        user_id: str, 
        update_data: UserUpdate,
        current_user: UserModel
    ) -> Dict[str, Any]:
        """Update user profile with validation and security checks"""
        try:
            if not validate_object_id(user_id):
                raise ValidationError("Invalid user ID format", "user_id", user_id)
            
            # Check if user can update this profile
            if str(current_user._id) != user_id and not current_user.can_manage_users():
                raise AuthorizationError("Cannot update other user's profile")
            
            # Validate update data
            if update_data.email:
                # Check if email is already taken by another user
                existing_user = await self.db.users.find_one({
                    "email": update_data.email,
                    "_id": {"$ne": ObjectId(user_id)}
                })
                if existing_user:
                    raise ConflictError("Email already registered", "email")
            
            if update_data.phone_number:
                # Check if phone number is already taken
                existing_user = await self.db.users.find_one({
                    "phone_number": update_data.phone_number,
                    "_id": {"$ne": ObjectId(user_id)}
                })
                if existing_user:
                    raise ConflictError("Phone number already registered", "phone_number")
            
            # Prepare update fields
            update_fields = {}
            for field, value in update_data.dict(exclude_unset=True).items():
                if value is not None:
                    update_fields[field] = value
            
            if not update_fields:
                raise ValidationError("No valid fields to update")
            
            update_fields["updated_at"] = datetime.utcnow()
            
            # Update user in database
            result = await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_fields}
            )
            
            if result.matched_count == 0:
                raise ResourceNotFoundError("User", user_id)
            
            # Get updated user data
            updated_user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            updated_user["_id"] = str(updated_user["_id"])
            
            logger.info(f"User profile updated: {user_id}")
            return updated_user
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            raise DatabaseError("Failed to update user profile", "update_user_profile")
    
    async def get_students(
        self,
        department: Optional[str] = None,
        level: Optional[str] = None,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        search_query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        current_user: UserModel = None
    ) -> Dict[str, Any]:
        """Get students with comprehensive filtering, search, and pagination"""
        try:
            # Check permissions
            if current_user and not current_user.can_manage_users():
                raise AuthorizationError("Insufficient privileges to view student list")
            
            # Build filter query
            filter_query = {"role": {"$in": [UserRole.STUDENT.value, UserRole.DEPARTMENT_ADMIN.value]}}
            
            if department:
                filter_query["department"] = department
            if level:
                filter_query["level"] = level
            if role:
                filter_query["role"] = role.value
            if status:
                filter_query["status"] = status.value
            
            # Text search across multiple fields
            if search_query:
                search_regex = {"$regex": search_query, "$options": "i"}
                filter_query["$or"] = [
                    {"full_name": search_regex},
                    {"student_id": search_regex},
                    {"email": search_regex},
                    {"department": search_regex}
                ]
            
            # Get total count
            total_count = await self.db.users.count_documents(filter_query)
            
            # Get students with pagination
            cursor = self.db.users.find(filter_query).sort("full_name", 1).skip(skip).limit(limit)
            students = []
            
            async for student in cursor:
                student["_id"] = str(student["_id"])
                # Remove sensitive information
                student.pop("password_hash", None)
                students.append(student)
            
            return {
                "total_count": total_count,
                "students": students,
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "has_more": skip + limit < total_count
                },
                "filters": {
                    "department": department,
                    "level": level,
                    "role": role.value if role else None,
                    "status": status.value if status else None,
                    "search_query": search_query
                }
            }
            
        except CustomHTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting students: {str(e)}")
            raise DatabaseError("Failed to retrieve student list", "get_students")
    
    async def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """Get user by ID with basic information"""
        try:
            if not validate_object_id(user_id):
                raise ValidationError("Invalid user ID format", "user_id", user_id)
            
            user_data = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user_data:
                raise ResourceNotFoundError("User", user_id)
            
            # Remove sensitive information
            user_data["_id"] = str(user_data["_id"])
            user_data.pop("password_hash", None)
            
            return user_data
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            raise DatabaseError("Failed to retrieve user", "get_user_by_id")
    
    async def deactivate_user(self, user_id: str, current_user: UserModel) -> Dict[str, str]:
        """Deactivate user account (soft delete)"""
        try:
            if not validate_object_id(user_id):
                raise ValidationError("Invalid user ID format", "user_id", user_id)
            
            # Check permissions
            if not current_user.can_manage_users():
                raise AuthorizationError("Insufficient privileges to deactivate users")
            
            # Cannot deactivate self
            if str(current_user._id) == user_id:
                raise ValidationError("Cannot deactivate your own account")
            
            # Check if user exists
            user_data = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user_data:
                raise ResourceNotFoundError("User", user_id)
            
            # Soft delete - mark as inactive
            result = await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "status": UserStatus.INACTIVE.value,
                        "is_active": False,
                        "deactivated_at": datetime.utcnow(),
                        "deactivated_by": str(current_user._id),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.matched_count == 0:
                raise ResourceNotFoundError("User", user_id)
            
            logger.info(f"User deactivated: {user_id} by {current_user._id}")
            return {"message": "User deactivated successfully"}
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error deactivating user: {str(e)}")
            raise DatabaseError("Failed to deactivate user", "deactivate_user")
    
    async def reactivate_user(self, user_id: str, current_user: UserModel) -> Dict[str, str]:
        """Reactivate user account"""
        try:
            if not validate_object_id(user_id):
                raise ValidationError("Invalid user ID format", "user_id", user_id)
            
            # Check permissions
            if not current_user.can_manage_users():
                raise AuthorizationError("Insufficient privileges to reactivate users")
            
            # Check if user exists
            user_data = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user_data:
                raise ResourceNotFoundError("User", user_id)
            
            # Reactivate user
            result = await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "status": UserStatus.ACTIVE.value,
                        "is_active": True,
                        "reactivated_at": datetime.utcnow(),
                        "reactivated_by": str(current_user._id),
                        "updated_at": datetime.utcnow()
                    },
                    "$unset": {
                        "deactivated_at": "",
                        "deactivated_by": ""
                    }
                }
            )
            
            if result.matched_count == 0:
                raise ResourceNotFoundError("User", user_id)
            
            logger.info(f"User reactivated: {user_id} by {current_user._id}")
            return {"message": "User reactivated successfully"}
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error reactivating user: {str(e)}")
            raise DatabaseError("Failed to reactivate user", "reactivate_user")
    
    async def _get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        try:
            # Get attendance stats
            attendance_stats = await self.db.attendance.aggregate([
                {"$match": {"user_id": ObjectId(user_id)}},
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1}
                    }
                }
            ]).to_list(None)
            
            attendance_by_status = {item["_id"]: item["count"] for item in attendance_stats}
            
            # Get recent activity
            recent_activity = await self.db.attendance.find(
                {"user_id": ObjectId(user_id)}
            ).sort("created_at", -1).limit(5).to_list(None)
            
            # Format recent activity
            for activity in recent_activity:
                activity["_id"] = str(activity["_id"])
                activity["class_id"] = str(activity["class_id"])
                activity["user_id"] = str(activity["user_id"])
            
            return {
                "attendance_by_status": attendance_by_status,
                "total_attendance": sum(attendance_by_status.values()),
                "recent_activity": recent_activity,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return {
                "attendance_by_status": {},
                "total_attendance": 0,
                "recent_activity": [],
                "last_updated": datetime.utcnow().isoformat()
            }

# API Endpoints
@router.get("/profile", response_model=Dict[str, Any])
async def get_user_profile(
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get current user's detailed profile with statistics"""
    try:
        db = get_database()
        service = UserService(db)
        
        result = await service.get_user_profile(str(current_user._id))
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_user_profile endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/profile", response_model=Dict[str, Any])
async def update_user_profile(
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Update current user's profile"""
    try:
        db = get_database()
        service = UserService(db)
        
        result = await service.update_user_profile(
            str(current_user._id), user_update, current_user
        )
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_user_profile endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/students", response_model=Dict[str, Any])
async def get_students(
    department: Optional[str] = Query(None, description="Filter by department"),
    level: Optional[str] = Query(None, description="Filter by level"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    status: Optional[UserStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search query for name, ID, email, or department"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get students with comprehensive filtering, search, and pagination (admin only)"""
    try:
        db = get_database()
        service = UserService(db)
        
        result = await service.get_students(
            department=department,
            level=level,
            role=role,
            status=status,
            search_query=search,
            skip=skip,
            limit=limit,
            current_user=current_user
        )
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_students endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/users/{user_id}", response_model=Dict[str, Any])
async def get_user_by_id(
    user_id: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get user by ID (admin only)"""
    try:
        db = get_database()
        service = UserService(db)
        
        result = await service.get_user_by_id(user_id)
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_user_by_id endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/users/{user_id}/deactivate", response_model=Dict[str, str])
async def deactivate_user(
    user_id: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Deactivate user account (admin only)"""
    try:
        db = get_database()
        service = UserService(db)
        
        result = await service.deactivate_user(user_id, current_user)
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in deactivate_user endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/users/{user_id}/reactivate", response_model=Dict[str, str])
async def reactivate_user(
    user_id: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Reactivate user account (admin only)"""
    try:
        db = get_database()
        service = UserService(db)
        
        result = await service.reactivate_user(user_id, current_user)
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reactivate_user endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/users/{user_id}/stats", response_model=Dict[str, Any])
async def get_user_stats(
    user_id: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get user statistics (admin or self)"""
    try:
        # Check if user can view these stats
        if str(current_user._id) != user_id and not current_user.can_manage_users():
            raise AuthorizationError("Cannot view other user's statistics")
        
        db = get_database()
        service = UserService(db)
        
        result = await service._get_user_stats(user_id)
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_user_stats endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 