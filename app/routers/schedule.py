from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date, time
import logging
from bson import ObjectId
import json
from enum import Enum

from ..database import get_database
from ..schemas.schedule import (
    ScheduleCreate, ScheduleUpdate, ScheduleConflict, ScheduleStats,
    ClassSchedule, StudentSchedule, TodaySchedule, NextClass,
    DayOfWeek, ScheduleType
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

class ScheduleService:
    def __init__(self, db):
        self.db = db
    
    async def create_schedule(
        self, 
        schedule_data: ScheduleCreate, 
        user_id: str
    ) -> Dict[str, Any]:
        """Create a new schedule with conflict detection"""
        try:
            # Validate user exists and has permission
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise ResourceNotFoundError("User", user_id)
            
            # Check for schedule conflicts
            conflicts = await self._check_schedule_conflicts(
                user_id, 
                schedule_data.date, 
                schedule_data.start_time, 
                schedule_data.end_time
            )
            
            if conflicts:
                raise ConflictError(
                    f"Schedule conflicts with existing events: {', '.join(conflicts)}",
                    "schedule_time"
                )
            
            # Create schedule document
            schedule_doc = {
                "user_id": ObjectId(user_id),
                "title": schedule_data.title,
                "description": schedule_data.description,
                "date": schedule_data.date,
                "start_time": schedule_data.start_time,
                "end_time": schedule_data.end_time,
                "location": schedule_data.location,
                "type": schedule_data.type,
                "priority": schedule_data.priority,
                "is_recurring": schedule_data.is_recurring,
                "recurrence_pattern": schedule_data.recurrence_pattern,
                "reminder_minutes": schedule_data.reminder_minutes,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await self.db.schedules.insert_one(schedule_doc)
            schedule_doc["_id"] = str(result.inserted_id)
            schedule_doc["user_id"] = str(schedule_doc["user_id"])
            
            # Create notification if reminder is set
            if schedule_data.reminder_minutes:
                await self._create_notification(
                    str(result.inserted_id),
                    user_id,
                    schedule_data.title,
                    schedule_data.date,
                    schedule_data.start_time,
                    schedule_data.reminder_minutes
                )
            
            logger.info(f"Schedule created: {schedule_data.title} for user {user_id}")
            return schedule_doc
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error creating schedule: {str(e)}")
            raise DatabaseError("Failed to create schedule", "create_schedule")
    
    async def get_schedules(
        self,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        schedule_type: Optional[str] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get user schedules with comprehensive filtering and pagination"""
        try:
            if not validate_object_id(user_id):
                raise ValidationError("Invalid user ID format", "user_id", user_id)
            
            # Build filter query
            filter_query = {"user_id": ObjectId(user_id), "is_active": is_active}
            
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                filter_query["date"] = date_filter
            
            if schedule_type:
                filter_query["type"] = schedule_type
            
            # Get total count
            total_count = await self.db.schedules.count_documents(filter_query)
            
            # Get schedules with pagination
            cursor = self.db.schedules.find(filter_query).sort("date", 1).skip(skip).limit(limit)
            schedules = []
            
            async for schedule in cursor:
                schedule["_id"] = str(schedule["_id"])
                schedule["user_id"] = str(schedule["user_id"])
                schedules.append(schedule)
            
            return {
                "total_count": total_count,
                "schedules": schedules,
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "has_more": skip + limit < total_count
                },
                "filters": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "type": schedule_type,
                    "is_active": is_active
                }
            }
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting schedules: {str(e)}")
            raise DatabaseError("Failed to retrieve schedules", "get_schedules")
    
    async def get_today_schedule(self, user_id: str) -> List[Dict[str, Any]]:
        """Get today's schedule for user"""
        try:
            if not validate_object_id(user_id):
                raise ValidationError("Invalid user ID format", "user_id", user_id)
            
            today = date.today()
            
            # Get today's schedules
            cursor = self.db.schedules.find({
                "user_id": ObjectId(user_id),
                "date": today,
                "is_active": True
            }).sort("start_time", 1)
            
            schedules = []
            async for schedule in cursor:
                schedule["_id"] = str(schedule["_id"])
                schedule["user_id"] = str(schedule["user_id"])
                schedules.append(schedule)
            
            return schedules
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting today's schedule: {str(e)}")
            raise DatabaseError("Failed to retrieve today's schedule", "get_today_schedule")
    
    async def get_next_class(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's next upcoming class"""
        try:
            if not validate_object_id(user_id):
                raise ValidationError("Invalid user ID format", "user_id", user_id)
            
            now = datetime.utcnow()
            current_time = now.time()
            today = now.date()
            
            # Find next class today
            next_class = await self.db.schedules.find_one({
                "user_id": ObjectId(user_id),
                "date": today,
                "start_time": {"$gt": current_time},
                "type": "class",
                "is_active": True
            }, sort=[("start_time", 1)])
            
            if next_class:
                next_class["_id"] = str(next_class["_id"])
                next_class["user_id"] = str(next_class["user_id"])
                
                # Calculate time until class
                class_datetime = datetime.combine(today, next_class["start_time"])
                time_until = class_datetime - now
                next_class["minutes_until"] = int(time_until.total_seconds() / 60)
                
                return next_class
            
            # If no class today, find next class in future days
            future_class = await self.db.schedules.find_one({
                "user_id": ObjectId(user_id),
                "date": {"$gt": today},
                "type": "class",
                "is_active": True
            }, sort=[("date", 1), ("start_time", 1)])
            
            if future_class:
                future_class["_id"] = str(future_class["_id"])
                future_class["user_id"] = str(future_class["user_id"])
                
                # Calculate days until class
                days_until = (future_class["date"] - today).days
                future_class["days_until"] = days_until
                
                return future_class
            
            return None
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting next class: {str(e)}")
            raise DatabaseError("Failed to retrieve next class", "get_next_class")
    
    async def update_schedule(
        self,
        schedule_id: str,
        update_data: ScheduleUpdate,
        user_id: str
    ) -> Dict[str, Any]:
        """Update schedule with validation and conflict detection"""
        try:
            if not validate_object_id(schedule_id):
                raise ValidationError("Invalid schedule ID format", "schedule_id", schedule_id)
            
            if not validate_object_id(user_id):
                raise ValidationError("Invalid user ID format", "user_id", user_id)
            
            # Check if schedule exists and belongs to user
            schedule = await self.db.schedules.find_one({
                "_id": ObjectId(schedule_id),
                "user_id": ObjectId(user_id)
            })
            
            if not schedule:
                raise ResourceNotFoundError("Schedule", schedule_id)
            
            # Check for conflicts if time is being updated
            if update_data.start_time or update_data.end_time:
                start_time = update_data.start_time or schedule["start_time"]
                end_time = update_data.end_time or schedule["end_time"]
                date_val = update_data.date or schedule["date"]
                
                conflicts = await self._check_schedule_conflicts(
                    user_id, date_val, start_time, end_time, exclude_id=schedule_id
                )
                
                if conflicts:
                    raise ConflictError(
                        f"Schedule conflicts with existing events: {', '.join(conflicts)}",
                        "schedule_time"
                    )
            
            # Prepare update fields
            update_fields = {}
            for field, value in update_data.dict(exclude_unset=True).items():
                if value is not None:
                    update_fields[field] = value
            
            if not update_fields:
                raise ValidationError("No valid fields to update")
            
            update_fields["updated_at"] = datetime.utcnow()
            
            # Update schedule
            result = await self.db.schedules.update_one(
                {"_id": ObjectId(schedule_id)},
                {"$set": update_fields}
            )
            
            if result.matched_count == 0:
                raise ResourceNotFoundError("Schedule", schedule_id)
            
            # Get updated schedule
            updated_schedule = await self.db.schedules.find_one({"_id": ObjectId(schedule_id)})
            updated_schedule["_id"] = str(updated_schedule["_id"])
            updated_schedule["user_id"] = str(updated_schedule["user_id"])
            
            logger.info(f"Schedule updated: {schedule_id} by user {user_id}")
            return updated_schedule
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error updating schedule: {str(e)}")
            raise DatabaseError("Failed to update schedule", "update_schedule")
    
    async def delete_schedule(self, schedule_id: str, user_id: str) -> Dict[str, str]:
        """Delete schedule (soft delete)"""
        try:
            if not validate_object_id(schedule_id):
                raise ValidationError("Invalid schedule ID format", "schedule_id", schedule_id)
            
            if not validate_object_id(user_id):
                raise ValidationError("Invalid user ID format", "user_id", user_id)
            
            # Check if schedule exists and belongs to user
            schedule = await self.db.schedules.find_one({
                "_id": ObjectId(schedule_id),
                "user_id": ObjectId(user_id)
            })
            
            if not schedule:
                raise ResourceNotFoundError("Schedule", schedule_id)
            
            # Soft delete
            result = await self.db.schedules.update_one(
                {"_id": ObjectId(schedule_id)},
                {
                    "$set": {
                        "is_active": False,
                        "deleted_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.matched_count == 0:
                raise ResourceNotFoundError("Schedule", schedule_id)
            
            logger.info(f"Schedule deleted: {schedule_id} by user {user_id}")
            return {"message": "Schedule deleted successfully"}
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error deleting schedule: {str(e)}")
            raise DatabaseError("Failed to delete schedule", "delete_schedule")
    
    async def get_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's notification settings and upcoming notifications"""
        try:
            if not validate_object_id(user_id):
                raise ValidationError("Invalid user ID format", "user_id", user_id)
            
            # Get notification settings
            settings = await self.db.notification_settings.find_one({"user_id": ObjectId(user_id)})
            
            # Get upcoming notifications
            now = datetime.utcnow()
            upcoming_notifications = await self.db.notifications.find({
                "user_id": ObjectId(user_id),
                "scheduled_time": {"$gt": now},
                "is_sent": False
            }).sort("scheduled_time", 1).limit(10).to_list(None)
            
            # Format notifications
            for notification in upcoming_notifications:
                notification["_id"] = str(notification["_id"])
                notification["user_id"] = str(notification["user_id"])
                notification["schedule_id"] = str(notification["schedule_id"])
            
            return {
                "settings": settings or {},
                "upcoming_notifications": upcoming_notifications
            }
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error getting notifications: {str(e)}")
            raise DatabaseError("Failed to retrieve notifications", "get_notifications")
    
    async def update_notifications(
        self,
        user_id: str,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user's notification settings"""
        try:
            if not validate_object_id(user_id):
                raise ValidationError("Invalid user ID format", "user_id", user_id)
            
            # Upsert notification settings
            result = await self.db.notification_settings.update_one(
                {"user_id": ObjectId(user_id)},
                {
                    "$set": {
                        **settings.dict(),
                        "user_id": ObjectId(user_id),
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            # Get updated settings
            updated_settings = await self.db.notification_settings.find_one({"user_id": ObjectId(user_id)})
            updated_settings["_id"] = str(updated_settings["_id"])
            updated_settings["user_id"] = str(updated_settings["user_id"])
            
            logger.info(f"Notification settings updated for user {user_id}")
            return updated_settings
            
        except (CustomHTTPException, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error updating notification settings: {str(e)}")
            raise DatabaseError("Failed to update notification settings", "update_notifications")
    
    async def _check_schedule_conflicts(
        self,
        user_id: str,
        date_val: date,
        start_time: time,
        end_time: time,
        exclude_id: Optional[str] = None
    ) -> List[str]:
        """Check for schedule conflicts"""
        try:
            conflict_query = {
                "user_id": ObjectId(user_id),
                "date": date_val,
                "is_active": True,
                "$or": [
                    {
                        "start_time": {"$lt": end_time},
                        "end_time": {"$gt": start_time}
                    }
                ]
            }
            
            if exclude_id:
                conflict_query["_id"] = {"$ne": ObjectId(exclude_id)}
            
            conflicting_schedules = await self.db.schedules.find(conflict_query).to_list(None)
            
            conflicts = []
            for schedule in conflicting_schedules:
                conflicts.append(schedule["title"])
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Error checking schedule conflicts: {str(e)}")
            return []
    
    async def _create_notification(
        self,
        schedule_id: str,
        user_id: str,
        title: str,
        schedule_date: date,
        start_time: time,
        reminder_minutes: int
    ):
        """Create notification for schedule reminder"""
        try:
            notification_time = datetime.combine(schedule_date, start_time) - timedelta(minutes=reminder_minutes)
            
            notification_doc = {
                "user_id": ObjectId(user_id),
                "schedule_id": ObjectId(schedule_id),
                "title": f"Reminder: {title}",
                "message": f"Your schedule '{title}' starts in {reminder_minutes} minutes",
                "scheduled_time": notification_time,
                "is_sent": False,
                "created_at": datetime.utcnow()
            }
            
            await self.db.notifications.insert_one(notification_doc)
            
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")

# API Endpoints
@router.post("/schedules", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: UserModel = Depends(get_current_active_user),
    background_tasks: BackgroundTasks = None
):
    """Create a new schedule with conflict detection"""
    try:
        db = get_database()
        service = ScheduleService(db)
        
        result = await service.create_schedule(schedule_data, str(current_user._id))
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_schedule endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/schedules", response_model=Dict[str, Any])
async def get_schedules(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    type: Optional[str] = Query(None, description="Filter by schedule type"),
    active_only: bool = Query(True, description="Show only active schedules"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get user schedules with comprehensive filtering and pagination"""
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Invalid start date format. Use YYYY-MM-DD", "start_date", start_date)
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Invalid end date format. Use YYYY-MM-DD", "end_date", end_date)
        
        if start_dt and end_dt and start_dt > end_dt:
            raise ValidationError("Start date cannot be after end date")
        
        db = get_database()
        service = ScheduleService(db)
        
        result = await service.get_schedules(
            str(current_user._id), start_dt, end_dt, type, active_only, skip, limit
        )
        return result
        
    except (CustomHTTPException, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error in get_schedules endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/schedules/today", response_model=List[Dict[str, Any]])
async def get_today_schedule(
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get today's schedule for current user"""
    try:
        db = get_database()
        service = ScheduleService(db)
        
        result = await service.get_today_schedule(str(current_user._id))
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_today_schedule endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/schedules/next-class", response_model=Optional[Dict[str, Any]])
async def get_next_class(
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get user's next upcoming class"""
    try:
        db = get_database()
        service = ScheduleService(db)
        
        result = await service.get_next_class(str(current_user._id))
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_next_class endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/schedules/{schedule_id}", response_model=Dict[str, Any])
async def update_schedule(
    schedule_id: str,
    schedule_update: ScheduleUpdate,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Update schedule with validation and conflict detection"""
    try:
        db = get_database()
        service = ScheduleService(db)
        
        result = await service.update_schedule(schedule_id, schedule_update, str(current_user._id))
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_schedule endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/schedules/{schedule_id}", response_model=Dict[str, str])
async def delete_schedule(
    schedule_id: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Delete schedule (soft delete)"""
    try:
        db = get_database()
        service = ScheduleService(db)
        
        result = await service.delete_schedule(schedule_id, str(current_user._id))
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_schedule endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/schedules/notifications", response_model=Dict[str, Any])
async def get_notifications(
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get user's notification settings and upcoming notifications"""
    try:
        db = get_database()
        service = ScheduleService(db)
        
        result = await service.get_notifications(str(current_user._id))
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_notifications endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/schedules/notifications", response_model=Dict[str, Any])
async def update_notifications(
    settings: Dict[str, Any],
    current_user: UserModel = Depends(get_current_active_user)
):
    """Update user's notification settings"""
    try:
        db = get_database()
        service = ScheduleService(db)
        
        result = await service.update_notifications(str(current_user._id), settings)
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_notifications endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 