"""
Flask Attendance Router
Full attendance management functionality
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from datetime import datetime, timedelta
from bson import ObjectId
import hashlib
import secrets
import json

from ..database import get_database
from ..core.exceptions import CustomHTTPException
from ..core.qr_generator import LightweightQRGenerator

logger = logging.getLogger(__name__)

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/classes', methods=['POST'])
@jwt_required()
def create_class():
    """Create a new class (instructors only)"""
    try:
        current_user_email = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'course_code', 'department', 'level', 'date', 'start_time', 'end_time', 'location']
        for field in required_fields:
            if not data.get(field):
                raise CustomHTTPException(400, f"Missing required field: {field}")
        
        db = get_database()
        
        # Check if current user is instructor
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user or not current_user.get('is_instructor', False):
            raise CustomHTTPException(403, "Only instructors can create classes")
        
        # Parse date and times
        try:
            class_date = datetime.strptime(data['date'], "%Y-%m-%d")
            start_time = datetime.strptime(data['start_time'], "%H:%M").time()
            end_time = datetime.strptime(data['end_time'], "%H:%M").time()
        except ValueError:
            raise CustomHTTPException(400, "Invalid date or time format")
        
        # Check for class conflicts
        conflict_query = {
            "instructor_id": str(current_user['_id']),
            "date": class_date,
            "$or": [
                {
                    "start_time": {"$lt": end_time},
                    "end_time": {"$gt": start_time}
                }
            ]
        }
        
        existing_conflict = db.classes.find_one(conflict_query)
        if existing_conflict:
            raise CustomHTTPException(409, "Class time conflicts with existing class")
        
        # Create class document
        class_doc = {
            "name": data['name'],
            "course_code": data['course_code'],
            "instructor_id": str(current_user['_id']),
            "instructor_name": current_user.get('full_name'),
            "department": data['department'],
            "level": data['level'],
            "date": class_date,
            "start_time": start_time,
            "end_time": end_time,
            "location": data['location'],
            "max_students": data.get('max_students', 50),
            "description": data.get('description', ''),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.classes.insert_one(class_doc)
        class_doc['_id'] = str(result.inserted_id)
        
        logger.info(f"Class created: {class_doc['course_code']} by instructor {current_user_email}")
        
        return jsonify({
            "message": "Class created successfully",
            "class": class_doc
        }), 201
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Create class error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@attendance_bp.route('/classes', methods=['GET'])
@jwt_required()
def get_classes():
    """Get classes with filtering and pagination"""
    try:
        db = get_database()
        
        # Get query parameters
        skip = int(request.args.get('skip', 0))
        limit = min(int(request.args.get('limit', 50)), 100)
        department = request.args.get('department')
        level = request.args.get('level')
        instructor_id = request.args.get('instructor_id')
        date = request.args.get('date')
        is_active = request.args.get('is_active', 'true').lower() == 'true'
        
        # Build filter query
        filter_query = {"is_active": is_active}
        
        if department:
            filter_query["department"] = department
        if level:
            filter_query["level"] = level
        if instructor_id:
            if not ObjectId.is_valid(instructor_id):
                raise CustomHTTPException(400, "Invalid instructor ID format")
            filter_query["instructor_id"] = instructor_id
        if date:
            try:
                filter_date = datetime.strptime(date, "%Y-%m-%d")
                filter_query["date"] = filter_date
            except ValueError:
                raise CustomHTTPException(400, "Invalid date format. Use YYYY-MM-DD")
        
        # Get total count
        total_count = db.classes.count_documents(filter_query)
        
        # Get classes with pagination
        classes_cursor = db.classes.find(filter_query).sort("date", -1).skip(skip).limit(limit)
        classes = []
        
        for class_data in classes_cursor:
            class_data['_id'] = str(class_data['_id'])
            classes.append(class_data)
        
        return jsonify({
            "classes": classes,
            "total_count": total_count,
            "pagination": {
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total_count
            }
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get classes error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@attendance_bp.route('/classes/<class_id>/qr-code', methods=['GET'])
@jwt_required()
def generate_qr_code(class_id):
    """Generate QR code for class attendance (instructors only)"""
    try:
        if not ObjectId.is_valid(class_id):
            raise CustomHTTPException(400, "Invalid class ID format")
        
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Check if current user is instructor
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user or not current_user.get('is_instructor', False):
            raise CustomHTTPException(403, "Only instructors can generate QR codes")
        
        # Get class information
        class_data = db.classes.find_one({"_id": ObjectId(class_id)})
        if not class_data:
            raise CustomHTTPException(404, "Class not found")
        
        # Check if instructor owns this class
        if str(class_data["instructor_id"]) != str(current_user["_id"]):
            raise CustomHTTPException(403, "Only class instructor can generate QR codes")
        
        # Check if class is active and not expired
        now = datetime.utcnow()
        class_date = class_data["date"]
        if class_date.date() < now.date():
            raise CustomHTTPException(400, "Cannot generate QR code for past classes")
        
        # Generate unique QR code data
        qr_data = {
            "class_id": class_id,
            "timestamp": now.isoformat(),
            "nonce": secrets.token_hex(16),
            "expires_at": (class_date + timedelta(hours=2)).isoformat()
        }
        
        qr_json = json.dumps(qr_data)
        qr_hash = hashlib.sha256(qr_json.encode()).hexdigest()
        
        # Create QR code using lightweight generator
        qr_info = LightweightQRGenerator.generate_qr_info(qr_json)
        qr_base64 = qr_info["base64_svg"]
        
        # Store QR code in database
        qr_doc = {
            "class_id": ObjectId(class_id),
            "qr_hash": qr_hash,
            "qr_data": qr_data,
            "expires_at": datetime.fromisoformat(qr_data["expires_at"]),
            "is_active": True,
            "created_at": now,
            "created_by": str(current_user["_id"])
        }
        
        db.qr_codes.insert_one(qr_doc)
        
        # Update class with QR code info
        db.classes.update_one(
            {"_id": ObjectId(class_id)},
            {"$set": {"current_qr_code": qr_hash, "qr_generated_at": now}}
        )
        
        logger.info(f"QR code generated for class {class_id}")
        
        return jsonify({
            "qr_code": qr_base64,
            "qr_hash": qr_hash,
            "expires_at": qr_data["expires_at"],
            "class_info": {
                "name": class_data["name"],
                "course_code": class_data["course_code"],
                "location": class_data["location"],
                "start_time": class_data["start_time"].strftime("%H:%M"),
                "end_time": class_data["end_time"].strftime("%H:%M")
            }
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate QR code error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@attendance_bp.route('/scan-qr', methods=['POST'])
@jwt_required()
def scan_qr_code():
    """Scan QR code to mark attendance"""
    try:
        current_user_email = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('qr_code'):
            raise CustomHTTPException(400, "QR code is required")
        
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Validate QR code
        qr_doc = db.qr_codes.find_one({"qr_hash": data['qr_code']})
        if not qr_doc:
            raise CustomHTTPException(400, "Invalid QR code")
        
        if not qr_doc["is_active"]:
            raise CustomHTTPException(400, "QR code is no longer active")
        
        # Check expiration
        if datetime.utcnow() > qr_doc["expires_at"]:
            raise CustomHTTPException(400, "QR code has expired")
        
        class_id = str(qr_doc["class_id"])
        
        # Check if already marked attendance
        existing_attendance = db.attendance.find_one({
            "class_id": ObjectId(class_id),
            "user_id": ObjectId(current_user["_id"]),
            "date": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
        })
        
        if existing_attendance:
            raise CustomHTTPException(409, "Attendance already marked for this class today")
        
        # Get class information
        class_data = db.classes.find_one({"_id": ObjectId(class_id)})
        if not class_data:
            raise CustomHTTPException(404, "Class not found")
        
        # Determine attendance status based on time
        now = datetime.utcnow()
        class_start = datetime.combine(class_data["date"].date(), class_data["start_time"])
        class_end = datetime.combine(class_data["date"].date(), class_data["end_time"])
        
        if now < class_start:
            status = "early"
        elif now <= class_start + timedelta(minutes=15):
            status = "present"
        elif now <= class_end:
            status = "late"
        else:
            status = "absent"
        
        # Create attendance record
        attendance_doc = {
            "class_id": ObjectId(class_id),
            "user_id": ObjectId(current_user["_id"]),
            "student_id": current_user["student_id"],
            "full_name": current_user["full_name"],
            "department": current_user["department"],
            "level": current_user["level"],
            "class_name": class_data["name"],
            "course_code": class_data["course_code"],
            "date": class_data["date"],
            "check_in_time": now,
            "status": status,
            "qr_code": data['qr_code'],
            "location": data.get('location', ''),
            "created_at": now,
            "updated_at": now
        }
        
        result = db.attendance.insert_one(attendance_doc)
        attendance_doc["_id"] = str(result.inserted_id)
        
        logger.info(f"Attendance marked: {current_user['student_id']} for class {class_data['course_code']}")
        
        return jsonify({
            "message": "Attendance marked successfully",
            "attendance_id": str(result.inserted_id),
            "status": status,
            "check_in_time": now.isoformat(),
            "class_info": {
                "name": class_data["name"],
                "course_code": class_data["course_code"],
                "location": class_data["location"]
            }
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Scan QR code error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@attendance_bp.route('/my-attendance', methods=['GET'])
@jwt_required()
def get_my_attendance():
    """Get current user's attendance records"""
    try:
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Get query parameters
        skip = int(request.args.get('skip', 0))
        limit = min(int(request.args.get('limit', 50)), 100)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status = request.args.get('status')
        
        # Build filter query
        filter_query = {"user_id": ObjectId(current_user["_id"])}
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    date_filter["$gte"] = start_dt
                except ValueError:
                    raise CustomHTTPException(400, "Invalid start date format. Use YYYY-MM-DD")
            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    date_filter["$lte"] = end_dt
                except ValueError:
                    raise CustomHTTPException(400, "Invalid end date format. Use YYYY-MM-DD")
            filter_query["date"] = date_filter
        
        if status:
            filter_query["status"] = status
        
        # Get total count
        total_count = db.attendance.count_documents(filter_query)
        
        # Get attendance records with pagination
        attendance_cursor = db.attendance.find(filter_query).sort("date", -1).skip(skip).limit(limit)
        attendance_records = []
        
        for record in attendance_cursor:
            record["_id"] = str(record["_id"])
            record["class_id"] = str(record["class_id"])
            record["user_id"] = str(record["user_id"])
            attendance_records.append(record)
        
        return jsonify({
            "attendance_records": attendance_records,
            "total_count": total_count,
            "pagination": {
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total_count
            }
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get my attendance error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@attendance_bp.route('/attendance-stats', methods=['GET'])
@jwt_required()
def get_attendance_stats():
    """Get attendance statistics for current user"""
    try:
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        department = current_user["department"]
        level = current_user["level"]
        
        # Calculate date ranges
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Get total classes for user's level and department
        total_classes = db.classes.count_documents({
            "department": department,
            "level": level,
            "date": {"$lte": now},
            "is_active": True
        })
        
        # Get attendance records
        attendance_pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(current_user["_id"]),
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
        
        attendance_by_status_result = list(db.attendance.aggregate(attendance_pipeline))
        attendance_by_status = {item["_id"]: item["count"] for item in attendance_by_status_result}
        
        # Calculate attendance rate
        total_attendance = sum(attendance_by_status.values())
        attendance_rate = (total_attendance / total_classes * 100) if total_classes > 0 else 0
        
        # Weekly attendance
        weekly_pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(current_user["_id"]),
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
        
        weekly_attendance = list(db.attendance.aggregate(weekly_pipeline))
        
        # Monthly attendance
        monthly_pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(current_user["_id"]),
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
        
        monthly_attendance = list(db.attendance.aggregate(monthly_pipeline))
        
        return jsonify({
            "total_classes": total_classes,
            "total_attendance": total_attendance,
            "attendance_rate": round(attendance_rate, 2),
            "attendance_by_status": attendance_by_status,
            "attendance_by_department": {department: total_attendance},
            "attendance_by_level": {level: total_attendance},
            "weekly_attendance": weekly_attendance,
            "monthly_attendance": monthly_attendance
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get attendance stats error: {e}")
        raise CustomHTTPException(500, "Internal server error")
