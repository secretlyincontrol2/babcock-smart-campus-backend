"""
Flask Schedule Router
Basic schedule management functionality
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from datetime import datetime, timedelta
from bson import ObjectId

from ..database import get_database
from ..core.exceptions import CustomHTTPException

logger = logging.getLogger(__name__)

schedule_bp = Blueprint('schedule', __name__)

@schedule_bp.route('/', methods=['GET'])
@jwt_required()
def get_schedule():
    """Get user's schedule"""
    try:
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Build filter query
        filter_query = {
            "department": current_user["department"],
            "level": current_user["level"],
            "is_active": True
        }
        
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
        
        # Get classes
        classes_cursor = db.classes.find(filter_query).sort("date", 1)
        schedule = []
        
        for class_data in classes_cursor:
            class_data['_id'] = str(class_data['_id'])
            class_data['instructor_id'] = str(class_data['instructor_id'])
            schedule.append(class_data)
        
        return jsonify({
            "schedule": schedule,
            "total_classes": len(schedule)
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get schedule error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@schedule_bp.route('/today', methods=['GET'])
@jwt_required()
def get_today_schedule():
    """Get today's schedule"""
    try:
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        today = datetime.utcnow().date()
        
        # Get today's classes
        filter_query = {
            "department": current_user["department"],
            "level": current_user["level"],
            "date": today,
            "is_active": True
        }
        
        classes_cursor = db.classes.find(filter_query).sort("start_time", 1)
        today_schedule = []
        
        for class_data in classes_cursor:
            class_data['_id'] = str(class_data['_id'])
            class_data['instructor_id'] = str(class_data['instructor_id'])
            today_schedule.append(class_data)
        
        return jsonify({
            "date": today.isoformat(),
            "schedule": today_schedule,
            "total_classes": len(today_schedule)
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get today schedule error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@schedule_bp.route('/week', methods=['GET'])
@jwt_required()
def get_week_schedule():
    """Get this week's schedule"""
    try:
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        # Get this week's classes
        filter_query = {
            "department": current_user["department"],
            "level": current_user["level"],
            "date": {
                "$gte": week_start,
                "$lte": week_end
            },
            "is_active": True
        }
        
        classes_cursor = db.classes.find(filter_query).sort("date", 1)
        week_schedule = []
        
        for class_data in classes_cursor:
            class_data['_id'] = str(class_data['_id'])
            class_data['instructor_id'] = str(class_data['instructor_id'])
            week_schedule.append(class_data)
        
        return jsonify({
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "schedule": week_schedule,
            "total_classes": len(week_schedule)
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get week schedule error: {e}")
        raise CustomHTTPException(500, "Internal server error")
