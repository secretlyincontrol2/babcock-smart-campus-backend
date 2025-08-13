"""
Flask Users Router
Full user management functionality
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from datetime import datetime
from bson import ObjectId
from typing import Dict, Any

from ..database import get_database
from ..core.exceptions import CustomHTTPException

logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
@jwt_required()
def get_users():
    """Get all users (admin only)"""
    try:
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Check if current user is admin
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user or not current_user.get('is_admin', False):
            raise CustomHTTPException(403, "Insufficient privileges")
        
        # Get query parameters
        skip = int(request.args.get('skip', 0))
        limit = min(int(request.args.get('limit', 50)), 100)
        department = request.args.get('department')
        level = request.args.get('level')
        is_active = request.args.get('is_active')
        
        # Build filter query
        filter_query = {}
        if department:
            filter_query["department"] = department
        if level:
            filter_query["level"] = level
        if is_active is not None:
            filter_query["is_active"] = is_active.lower() == 'true'
        
        # Get total count
        total_count = db.users.count_documents(filter_query)
        
        # Get users with pagination
        users_cursor = db.users.find(filter_query).skip(skip).limit(limit)
        users = []
        
        for user in users_cursor:
            user['_id'] = str(user['_id'])
            user.pop('password_hash', None)  # Remove sensitive data
            users.append(user)
        
        return jsonify({
            "users": users,
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
        logger.error(f"Get users error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@users_bp.route('/<user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """Get specific user by ID"""
    try:
        if not ObjectId.is_valid(user_id):
            raise CustomHTTPException(400, "Invalid user ID format")
        
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Check if current user is admin or requesting their own profile
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "Current user not found")
        
        # Allow users to view their own profile or admins to view any profile
        if not current_user.get('is_admin', False) and current_user_email != user_id:
            raise CustomHTTPException(403, "Insufficient privileges")
        
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise CustomHTTPException(404, "User not found")
        
        user['_id'] = str(user['_id'])
        user.pop('password_hash', None)  # Remove sensitive data
        
        return jsonify(user)
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user's profile"""
    try:
        current_user_email = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            raise CustomHTTPException(400, "No data provided")
        
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Fields that can be updated
        allowed_fields = ['full_name', 'department', 'level']
        update_data = {}
        
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        if not update_data:
            raise CustomHTTPException(400, "No valid fields to update")
        
        update_data['updated_at'] = datetime.utcnow()
        
        # Update user
        result = db.users.update_one(
            {"email": current_user_email},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise CustomHTTPException(400, "No changes made")
        
        # Get updated user
        updated_user = db.users.find_one({"email": current_user_email})
        updated_user['_id'] = str(updated_user['_id'])
        updated_user.pop('password_hash', None)
        
        logger.info(f"Profile updated: {current_user_email}")
        
        return jsonify({
            "message": "Profile updated successfully",
            "user": updated_user
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@users_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change current user's password"""
    try:
        current_user_email = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('current_password') or not data.get('new_password'):
            raise CustomHTTPException(400, "Current password and new password are required")
        
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Verify current password
        if not check_password_hash(current_user['password_hash'], data['current_password']):
            raise CustomHTTPException(400, "Current password is incorrect")
        
        # Hash new password
        new_password_hash = generate_password_hash(data['new_password'])
        
        # Update password
        result = db.users.update_one(
            {"email": current_user_email},
            {
                "$set": {
                    "password_hash": new_password_hash,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise CustomHTTPException(400, "Password update failed")
        
        logger.info(f"Password changed: {current_user_email}")
        
        return jsonify({
            "message": "Password changed successfully"
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@users_bp.route('/<user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Update user (admin only)"""
    try:
        if not ObjectId.is_valid(user_id):
            raise CustomHTTPException(400, "Invalid user ID format")
        
        current_user_email = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            raise CustomHTTPException(400, "No data provided")
        
        db = get_database()
        
        # Check if current user is admin
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user or not current_user.get('is_admin', False):
            raise CustomHTTPException(403, "Insufficient privileges")
        
        # Fields that can be updated by admin
        allowed_fields = ['full_name', 'department', 'level', 'is_active', 'is_admin']
        update_data = {}
        
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        if not update_data:
            raise CustomHTTPException(400, "No valid fields to update")
        
        update_data['updated_at'] = datetime.utcnow()
        
        # Update user
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise CustomHTTPException(400, "No changes made")
        
        logger.info(f"User updated by admin: {user_id}")
        
        return jsonify({
            "message": "User updated successfully"
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@users_bp.route('/<user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Delete user (admin only)"""
    try:
        if not ObjectId.is_valid(user_id):
            raise CustomHTTPException(400, "Invalid user ID format")
        
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Check if current user is admin
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user or not current_user.get('is_admin', False):
            raise CustomHTTPException(403, "Insufficient privileges")
        
        # Prevent admin from deleting themselves
        if current_user['_id'] == ObjectId(user_id):
            raise CustomHTTPException(400, "Cannot delete your own account")
        
        # Delete user
        result = db.users.delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count == 0:
            raise CustomHTTPException(404, "User not found")
        
        logger.info(f"User deleted by admin: {user_id}")
        
        return jsonify({
            "message": "User deleted successfully"
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@users_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    """Get user statistics (admin only)"""
    try:
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Check if current user is admin
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user or not current_user.get('is_admin', False):
            raise CustomHTTPException(403, "Insufficient privileges")
        
        # Get statistics
        total_users = db.users.count_documents({})
        active_users = db.users.count_documents({"is_active": True})
        inactive_users = db.users.count_documents({"is_active": False})
        admin_users = db.users.count_documents({"is_admin": True})
        
        # Department breakdown
        dept_pipeline = [
            {"$group": {"_id": "$department", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        dept_breakdown = list(db.users.aggregate(dept_pipeline))
        
        # Level breakdown
        level_pipeline = [
            {"$group": {"_id": "$level", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        level_breakdown = list(db.users.aggregate(level_pipeline))
        
        return jsonify({
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "admin_users": admin_users,
            "department_breakdown": dept_breakdown,
            "level_breakdown": level_breakdown
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user stats error: {e}")
        raise CustomHTTPException(500, "Internal server error")
