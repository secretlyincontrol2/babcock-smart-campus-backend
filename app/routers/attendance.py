from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, time
import qrcode
import io
import base64
import json
import logging
from bson import ObjectId
from bson.errors import InvalidId
import hashlib
import secrets

from ..database import get_database
from ..schemas.attendance import (
    AttendanceCreate, AttendanceUpdate, ClassCreate, ClassResponse,
    AttendanceStats, AttendanceReport, QRCodeGenerate, QRCodeScan, QRCodeValidation,
    AttendanceStatus, ClassAttendance
)
from ..core.auth import get_current_active_user
from ..models.user import UserModel
from ..core.utils import format_datetime, format_object_id, validate_object_id
from ..core.exceptions import (
    CustomHTTPException, ValidationError, DatabaseError, 
    QRCodeExpiredError, DuplicateAttendanceError
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Rate limiting cache (in production, use Redis)
rate_limit_cache = {}

class AttendanceService:
    def __init__(self, db):
        self.db = db
    
    async def create_class(self, class_data: ClassCreate, instructor_id: str) -> ClassResponse:
        """Create a new class with comprehensive validation"""
        try:
            # Validate instructor exists and has permission
            instructor = await self.db.users.find_one({"_id": ObjectId(instructor_id)})
            if not instructor:
                raise CustomHTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Instructor not found"
                )
            
            # Check for class conflicts
            conflict_query = {
                "instructor_id": instructor_id,
                "date": class_data.date,
                "$or": [
                    {
                        "start_time": {"$lt": class_data.end_time},
                        "end_time": {"$gt": class_data.start_time}
                    }
                ]
            }
            
            existing_conflict = await self.db.classes.find_one(conflict_query)
            if existing_conflict:
                raise CustomHTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Class time conflicts with existing class"
                )
            
            # Create class document
            class_doc = {
                "name": class_data.name,
                "course_code": class_data.course_code,
                "instructor_id": instructor_id,
                "instructor_name": instructor.get("full_name"),
                "department": class_data.department,
                "level": class_data.level,
                "date": class_data.date,
                "start_time": class_data.start_time,
                "end_time": class_data.end_time,
                "location": class_data.location,
                "max_students": class_data.max_students,
                "description": class_data.description,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await self.db.classes.insert_one(class_doc)
            class_doc["_id"] = str(result.inserted_id)
            
            logger.info(f"Class created: {class_doc['course_code']} by instructor {instructor_id}")
            return ClassResponse(**class_doc)
            
        except CustomHTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating class: {str(e)}")
            raise DatabaseError("Failed to create class")
    
    async def generate_qr_code(self, class_id: str, instructor_id: str) -> Dict[str, Any]:
        """Generate QR code for class attendance"""
        try:
            # Validate class exists and instructor has permission
            class_data = await self.db.classes.find_one({"_id": ObjectId(class_id)})
            if not class_data:
                raise CustomHTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Class not found"
                )
            
            if str(class_data["instructor_id"]) != instructor_id:
                raise CustomHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only class instructor can generate QR codes"
                )
            
            # Check if class is active and not expired
            now = datetime.utcnow()
            class_date = class_data["date"]
            if class_date.date() < now.date():
                raise CustomHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot generate QR code for past classes"
                )
            
            # Generate unique QR code data
            qr_data = {
                "class_id": class_id,
                "timestamp": now.isoformat(),
                "nonce": secrets.token_hex(16),
                "expires_at": (class_date + timedelta(hours=2)).isoformat()
            }
            
            qr_json = json.dumps(qr_data)
            qr_hash = hashlib.sha256(qr_json.encode()).hexdigest()
            
            # Create QR code image
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_json)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Store QR code in database
            qr_doc = {
                "class_id": ObjectId(class_id),
                "qr_hash": qr_hash,
                "qr_data": qr_data,
                "expires_at": datetime.fromisoformat(qr_data["expires_at"]),
                "is_active": True,
                "created_at": now,
                "created_by": instructor_id
            }
            
            await self.db.qr_codes.insert_one(qr_doc)
            
            # Update class with QR code info
            await self.db.classes.update_one(
                {"_id": ObjectId(class_id)},
                {"$set": {"current_qr_code": qr_hash, "qr_generated_at": now}}
            )
            
            logger.info(f"QR code generated for class {class_id}")
            
            return {
                "qr_code": qr_base64,
                "qr_hash": qr_hash,
                "expires_at": qr_data["expires_at"],
                "class_info": {
                    "name": class_data["name"],
                    "course_code": class_data["course_code"],
                    "location": class_data["location"],
                    "start_time": class_data["start_time"],
                    "end_time": class_data["end_time"]
                }
            }
            
        except CustomHTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating QR code: {str(e)}")
            raise DatabaseError("Failed to generate QR code")
    
    async def scan_qr_code(self, qr_data: QRCodeScan, user_id: str) -> Dict[str, Any]:
        """Process QR code scan for attendance"""
        try:
            # Rate limiting check
            rate_key = f"qr_scan_{user_id}"
            if rate_key in rate_limit_cache:
                last_scan = rate_limit_cache[rate_key]
                if (datetime.utcnow() - last_scan).seconds < 30:  # 30 second cooldown
                    raise CustomHTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Please wait before scanning again"
                    )
            
            # Validate QR code
            qr_doc = await self.db.qr_codes.find_one({"qr_hash": qr_data.qr_code})
            if not qr_doc:
                raise CustomHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid QR code"
                )
            
            if not qr_doc["is_active"]:
                raise CustomHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="QR code is no longer active"
                )
            
            # Check expiration
            if datetime.utcnow() > qr_doc["expires_at"]:
                raise CustomHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="QR code has expired"
                )
            
            class_id = str(qr_doc["class_id"])
            
            # Check if already marked attendance
            existing_attendance = await self.db.attendance.find_one({
                "class_id": ObjectId(class_id),
                "user_id": ObjectId(user_id),
                "date": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
            })
            
            if existing_attendance:
                raise DuplicateAttendanceError("Attendance already marked for this class today")
            
            # Get class and user information
            class_data = await self.db.classes.find_one({"_id": ObjectId(class_id)})
            user_data = await self.db.users.find_one({"_id": ObjectId(user_id)})
            
            if not class_data or not user_data:
                raise CustomHTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Class or user not found"
                )
            
            # Determine attendance status based on time
            now = datetime.utcnow()
            class_start = datetime.combine(class_data["date"].date(), class_data["start_time"])
            class_end = datetime.combine(class_data["date"].date(), class_data["end_time"])
            
            if now < class_start:
                status = AttendanceStatus.EARLY
            elif now <= class_start + timedelta(minutes=15):
                status = AttendanceStatus.PRESENT
            elif now <= class_end:
                status = AttendanceStatus.LATE
            else:
                status = AttendanceStatus.ABSENT
            
            # Create attendance record
            attendance_doc = {
                "class_id": ObjectId(class_id),
                "user_id": ObjectId(user_id),
                "student_id": user_data["student_id"],
                "full_name": user_data["full_name"],
                "department": user_data["department"],
                "level": user_data["level"],
                "class_name": class_data["name"],
                "course_code": class_data["course_code"],
                "date": class_data["date"],
                "check_in_time": now,
                "status": status.value,
                "qr_code": qr_data.qr_code,
                "location": qr_data.location,
                "created_at": now,
                "updated_at": now
            }
            
            result = await self.db.attendance.insert_one(attendance_doc)
            attendance_doc["_id"] = str(result.inserted_id)
            
            # Update rate limiting
            rate_limit_cache[rate_key] = now
            
            # Log attendance
            logger.info(f"Attendance marked: {user_data['student_id']} for class {class_data['course_code']}")
            
            return {
                "message": "Attendance marked successfully",
                "attendance_id": str(result.inserted_id),
                "status": status.value,
                "check_in_time": now.isoformat(),
                "class_info": {
                    "name": class_data["name"],
                    "course_code": class_data["course_code"],
                    "location": class_data["location"]
                }
            }
            
        except (CustomHTTPException, DuplicateAttendanceError):
            raise
        except Exception as e:
            logger.error(f"Error scanning QR code: {str(e)}")
            raise DatabaseError("Failed to process attendance")
    
    async def get_my_attendance(
        self, 
        user_id: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[AttendanceStatus] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get user's attendance records with filtering and pagination"""
        try:
            # Build filter query
            filter_query = {"user_id": ObjectId(user_id)}
            
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                filter_query["date"] = date_filter
            
            if status:
                filter_query["status"] = status.value
            
            # Get total count
            total_count = await self.db.attendance.count_documents(filter_query)
            
            # Get attendance records
            cursor = self.db.attendance.find(filter_query).sort("date", -1).skip(skip).limit(limit)
            attendance_records = []
            
            async for record in cursor:
                record["_id"] = str(record["_id"])
                record["class_id"] = str(record["class_id"])
                record["user_id"] = str(record["user_id"])
                attendance_records.append(record)
            
            return {
                "total_count": total_count,
                "records": attendance_records,
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "has_more": skip + limit < total_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting attendance records: {str(e)}")
            raise DatabaseError("Failed to retrieve attendance records")
    
    async def get_attendance_stats(self, user_id: str) -> AttendanceStats:
        """Get comprehensive attendance statistics for user"""
        try:
            # Get user's department and level
            user_data = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user_data:
                raise CustomHTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            department = user_data["department"]
            level = user_data["level"]
            
            # Calculate date ranges
            now = datetime.utcnow()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            # Get total classes for user's level and department
            total_classes_pipeline = [
                {
                    "$match": {
                        "department": department,
                        "level": level,
                        "date": {"$lte": now},
                        "is_active": True
                    }
                },
                {"$count": "total"}
            ]
            
            total_classes_result = await self.db.classes.aggregate(total_classes_pipeline).to_list(1)
            total_classes = total_classes_result[0]["total"] if total_classes_result else 0
            
            # Get attendance records
            attendance_pipeline = [
                {
                    "$match": {
                        "user_id": ObjectId(user_id),
                        "date": {"$lte": now}
                    }
                },
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            attendance_by_status_result = await self.db.attendance.aggregate(attendance_pipeline).to_list(None)
            attendance_by_status = {item["_id"]: item["count"] for item in attendance_by_status_result}
            
            # Calculate attendance rate
            total_attendance = sum(attendance_by_status.values())
            attendance_rate = (total_attendance / total_classes * 100) if total_classes > 0 else 0
            
            # Weekly attendance
            weekly_pipeline = [
                {
                    "$match": {
                        "user_id": ObjectId(user_id),
                        "date": {"$gte": week_ago}
                    }
                },
                {
                    "$group": {
                        "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$date"}},
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"_id": 1}}
            ]
            
            weekly_attendance = await self.db.attendance.aggregate(weekly_pipeline).to_list(None)
            
            # Monthly attendance
            monthly_pipeline = [
                {
                    "$match": {
                        "user_id": ObjectId(user_id),
                        "date": {"$gte": month_ago}
                    }
                },
                {
                    "$group": {
                        "_id": {"$dateToString": {"format": "%Y-%m", "date": "$date"}},
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"_id": 1}}
            ]
            
            monthly_attendance = await self.db.attendance.aggregate(monthly_pipeline).to_list(None)
            
            return AttendanceStats(
                total_classes=total_classes,
                total_attendance=total_attendance,
                attendance_rate=round(attendance_rate, 2),
                attendance_by_status=attendance_by_status,
                attendance_by_department={department: total_attendance},
                attendance_by_level={level: total_attendance},
                weekly_attendance=weekly_attendance,
                monthly_attendance=monthly_attendance,
                class_performance=[]
            )
            
        except CustomHTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting attendance stats: {str(e)}")
            raise DatabaseError("Failed to retrieve attendance statistics")

# API Endpoints
@router.post("/classes", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
async def create_class(
    class_data: ClassCreate,
    current_user: UserModel = Depends(get_current_active_user),
    background_tasks: BackgroundTasks = None
):
    """Create a new class (instructors only)"""
    try:
        # Check permissions
        if not current_user.can_manage_classes():
            raise CustomHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges to create classes"
            )
        
        db = get_database()
        service = AttendanceService(db)
        
        result = await service.create_class(class_data, str(current_user._id))
        
        # Background task: Notify enrolled students
        if background_tasks:
            background_tasks.add_task(notify_students_new_class, class_data.department, class_data.level)
        
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_class endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/classes", response_model=List[ClassResponse])
async def get_classes(
    department: Optional[str] = Query(None, description="Filter by department"),
    level: Optional[str] = Query(None, description="Filter by level"),
    instructor_id: Optional[str] = Query(None, description="Filter by instructor"),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return")
):
    """Get classes with comprehensive filtering and pagination"""
    try:
        db = get_database()
        
        # Build filter query
        filter_query = {}
        
        if department:
            filter_query["department"] = department
        if level:
            filter_query["level"] = level
        if instructor_id:
            if not validate_object_id(instructor_id):
                raise CustomHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid instructor ID format"
                )
            filter_query["instructor_id"] = ObjectId(instructor_id)
        if date:
            try:
                filter_date = datetime.strptime(date, "%Y-%m-%d")
                filter_query["date"] = filter_date
            except ValueError:
                raise CustomHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        
        filter_query["is_active"] = is_active
        
        # Get total count
        total_count = await db.classes.count_documents(filter_query)
        
        # Get classes with pagination
        cursor = db.classes.find(filter_query).sort("date", -1).skip(skip).limit(limit)
        classes = []
        
        async for class_data in cursor:
            class_data["_id"] = str(class_data["_id"])
            class_data["instructor_id"] = str(class_data["instructor_id"])
            classes.append(ClassResponse(**class_data))
        
        return classes
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_classes endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/classes/{class_id}/qr-code")
async def get_qr_code(
    class_id: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Generate QR code for class attendance (instructors only)"""
    try:
        if not validate_object_id(class_id):
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid class ID format"
            )
        
        if not current_user.can_manage_classes():
            raise CustomHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges to generate QR codes"
            )
        
        db = get_database()
        service = AttendanceService(db)
        
        result = await service.generate_qr_code(class_id, str(current_user._id))
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_qr_code endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/scan-qr")
async def scan_qr(
    qr_data: QRCodeScan,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Scan QR code to mark attendance"""
    try:
        db = get_database()
        service = AttendanceService(db)
        
        result = await service.scan_qr_code(qr_data, str(current_user._id))
        return result
        
    except (CustomHTTPException, DuplicateAttendanceError) as e:
        if isinstance(e, DuplicateAttendanceError):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        raise
    except Exception as e:
        logger.error(f"Error in scan_qr endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/my-attendance")
async def get_my_attendance(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    status: Optional[AttendanceStatus] = Query(None, description="Filter by attendance status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get current user's attendance records with filtering and pagination"""
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise CustomHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start date format. Use YYYY-MM-DD"
                )
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise CustomHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end date format. Use YYYY-MM-DD"
                )
        
        if start_dt and end_dt and start_dt > end_dt:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date cannot be after end date"
            )
        
        db = get_database()
        service = AttendanceService(db)
        
        result = await service.get_my_attendance(
            str(current_user._id), start_dt, end_dt, status, skip, limit
        )
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_my_attendance endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/attendance-stats")
async def get_attendance_stats(
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get comprehensive attendance statistics for current user"""
    try:
        db = get_database()
        service = AttendanceService(db)
        
        result = await service.get_attendance_stats(str(current_user._id))
        return result
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_attendance_stats endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/classes/{class_id}/attendance-report")
async def get_class_attendance_report(
    class_id: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get detailed attendance report for a specific class (instructors only)"""
    try:
        if not validate_object_id(class_id):
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid class ID format"
            )
        
        if not current_user.can_manage_classes():
            raise CustomHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges to view attendance reports"
            )
        
        db = get_database()
        
        # Get class information
        class_data = await db.classes.find_one({"_id": ObjectId(class_id)})
        if not class_data:
            raise CustomHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class not found"
            )
        
        # Get attendance records for the class
        attendance_cursor = db.attendance.find({"class_id": ObjectId(class_id)})
        attendance_records = []
        
        async for record in attendance_cursor:
            record["_id"] = str(record["_id"])
            record["class_id"] = str(record["class_id"])
            record["user_id"] = str(record["user_id"])
            attendance_records.append(record)
        
        # Calculate statistics
        total_students = len(attendance_records)
        present_count = len([r for r in attendance_records if r["status"] == "present"])
        absent_count = len([r for r in attendance_records if r["status"] == "absent"])
        late_count = len([r for r in attendance_records if r["status"] == "late"])
        
        attendance_rate = (present_count / total_students * 100) if total_students > 0 else 0
        
        # Department and level breakdown
        dept_breakdown = {}
        level_breakdown = {}
        
        for record in attendance_records:
            dept = record["department"]
            level = record["level"]
            
            dept_breakdown[dept] = dept_breakdown.get(dept, 0) + 1
            level_breakdown[level] = level_breakdown.get(level, 0) + 1
        
        return AttendanceReport(
            class_id=class_id,
            class_name=class_data["name"],
            course_code=class_data["course_code"],
            date=class_data["date"],
            total_students=total_students,
            present_count=present_count,
            absent_count=absent_count,
            late_count=late_count,
            attendance_rate=round(attendance_rate, 2),
            attendance_list=attendance_records,
            department_breakdown=dept_breakdown,
            level_breakdown=level_breakdown
        )
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_class_attendance_report endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# Background task functions
async def notify_students_new_class(department: str, level: str):
    """Notify students about new class (background task)"""
    try:
        # In production, implement actual notification logic
        logger.info(f"Notifying students in {department} - {level} about new class")
    except Exception as e:
        logger.error(f"Error in notify_students_new_class: {str(e)}") 