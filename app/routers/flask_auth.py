"""
Flask Auth Router
Replaces FastAPI auth router for better deployment compatibility
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from datetime import datetime, timedelta
from bson import ObjectId

from ..database import get_database
from ..core.config import settings
from ..core.exceptions import CustomHTTPException

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'full_name', 'student_id', 'department', 'level']
        for field in required_fields:
            if not data.get(field):
                raise CustomHTTPException(400, f"Missing required field: {field}")
        
        db = get_database()
        
        # Check if user already exists
        existing_user = db.users.find_one({"email": data['email']})
        if existing_user:
            raise CustomHTTPException(400, "User with this email already exists")
        
        # Create user document with modern password hashing
        user_doc = {
            "email": data['email'],
            "password_hash": generate_password_hash(data['password'], method='scrypt'),
            "full_name": data['full_name'],
            "student_id": data['student_id'],
            "department": data['department'],
            "level": data['level'],
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.users.insert_one(user_doc)
        user_doc['_id'] = str(result.inserted_id)
        
        # Create access token
        access_token = create_access_token(identity=data['email'])
        refresh_token = create_refresh_token(identity=data['email'])
        
        logger.info(f"User registered: {data['email']}")
        
        return jsonify({
            "message": "User registered successfully",
            "user": {
                "id": str(result.inserted_id),
                "email": data['email'],
                "full_name": data['full_name'],
                "student_id": data['student_id'],
                "department": data['department'],
                "level": data['level']
            },
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 201
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            raise CustomHTTPException(400, "Email and password are required")
        
        db = get_database()
        
        # Find user
        user = db.users.find_one({"email": data['email']})
        if not user:
            raise CustomHTTPException(401, "Invalid credentials")
        
        # Check password - handle both old and new hash methods
        try:
            # Try modern scrypt method first
            if check_password_hash(user['password_hash'], data['password']):
                password_valid = True
            else:
                password_valid = False
        except Exception as e:
            logger.warning(f"Password check failed with modern method, trying legacy: {e}")
            # Fallback to legacy method for old password hashes
            try:
                from werkzeug.security import check_password_hash as legacy_check
                password_valid = legacy_check(user['password_hash'], data['password'])
            except Exception as legacy_error:
                logger.error(f"Legacy password check also failed: {legacy_error}")
                password_valid = False
        
        if not password_valid:
            raise CustomHTTPException(401, "Invalid credentials")
        
        # If password is valid and using old hash method, migrate to new method
        if password_valid and not user['password_hash'].startswith('scrypt$'):
            try:
                logger.info(f"Migrating password hash for user: {data['email']}")
                new_hash = generate_password_hash(data['password'], method='scrypt')
                db.users.update_one(
                    {"_id": user['_id']}, 
                    {"$set": {"password_hash": new_hash, "updated_at": datetime.utcnow()}}
                )
                logger.info(f"Password hash migrated successfully for user: {data['email']}")
            except Exception as migration_error:
                logger.warning(f"Password migration failed for user {data['email']}: {migration_error}")
                # Continue with login even if migration fails
        
        if not user.get('is_active', True):
            raise CustomHTTPException(401, "Account is deactivated")
        
        # Create tokens
        access_token = create_access_token(identity=data['email'])
        refresh_token = create_refresh_token(identity=data['email'])
        
        logger.info(f"User logged in: {data['email']}")
        
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": str(user['_id']),
                "email": user['email'],
                "full_name": user['full_name'],
                "student_id": user['student_id'],
                "department": user['department'],
                "level": user['level']
            },
            "access_token": access_token,
            "refresh_token": refresh_token
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@auth_bp.route('/login', methods=['GET'])
def login_get():
    """Handle GET requests to login endpoint"""
    return jsonify({
        "error": "Method not allowed",
        "message": "Use POST method for login",
        "example": {
            "method": "POST",
            "url": "/auth/login",
            "body": {
                "email": "user@example.com",
                "password": "password123"
            }
        }
    }), 405

@auth_bp.route('/register', methods=['GET'])
def register_get():
    """Handle GET requests to register endpoint"""
    return jsonify({
        "error": "Method not allowed",
        "message": "Use POST method for registration",
        "example": {
            "method": "POST",
            "url": "/auth/register",
            "body": {
                "email": "user@example.com",
                "password": "password123",
                "full_name": "John Doe",
                "student_id": "BU2024001",
                "department": "Computer Science",
                "level": "300"
            }
        }
    }), 405

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        current_user = get_jwt_identity()
        new_access_token = create_access_token(identity=current_user)
        
        return jsonify({
            "access_token": new_access_token
        })
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Handle specific JWT errors
        if "Invalid token" in str(e) or "Token has expired" in str(e):
            return jsonify({
                "error": "Invalid or expired refresh token",
                "message": "Please login again to get a new refresh token"
            }), 401
        else:
            return jsonify({
                "error": "Token refresh failed",
                "message": "An error occurred while refreshing the token"
            }), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information"""
    try:
        current_user_email = get_jwt_identity()
        db = get_database()
        
        user = db.users.find_one({"email": current_user_email})
        if not user:
            raise CustomHTTPException(404, "User not found")
        
        return jsonify({
            "id": str(user['_id']),
            "email": user['email'],
            "full_name": user['full_name'],
            "student_id": user['student_id'],
            "department": user['department'],
            "level": user['level'],
            "is_active": user.get('is_active', True),
            "created_at": user['created_at'].isoformat() if user.get('created_at') else None,
            "updated_at": user['updated_at'].isoformat() if user.get('updated_at') else None
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise CustomHTTPException(500, "Internal server error")
