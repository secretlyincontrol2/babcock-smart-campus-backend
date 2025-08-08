import logging
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from bson import ObjectId
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

from ..core.config import settings
from ..core.security import get_password_hash, verify_password, create_access_token
from ..database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    student_id: str
    email: str
    full_name: str
    password: str
    department: str
    level: str
    phone_number: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    student_id: str
    email: str
    full_name: str
    department: str
    level: str
    phone_number: Optional[str] = None
    is_active: bool
    is_verified: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Helper function to handle database operations with error handling
async def get_db_with_retry():
    """Get database with connection retry logic."""
    try:
        db = get_database()
        if db is None:
            # Try to reconnect
            from ..database import connect_to_mongo
            await connect_to_mongo()
            db = get_database()
            
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service is temporarily unavailable"
            )
        return db
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable. Please try again in a moment."
        )

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """Register a new user with proper error handling."""
    try:
        db = await get_db_with_retry()
        
        # Check if user already exists
        try:
            existing_user = await db.users.find_one({
                "$or": [
                    {"email": user_data.email}, 
                    {"student_id": user_data.student_id}
                ]
            })
            
            if existing_user:
                if existing_user.get("email") == user_data.email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, 
                        detail="User with this email already exists"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, 
                        detail="User with this student ID already exists"
                    )
        
        except (ServerSelectionTimeoutError, ConnectionFailure) as db_error:
            logger.error(f"Database error during user lookup: {db_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable. Please try again."
            )
        
        # Create user document
        user_doc = {
            "student_id": user_data.student_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "password_hash": get_password_hash(user_data.password),
            "department": user_data.department,
            "level": user_data.level,
            "phone_number": user_data.phone_number,
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        try:
            result = await db.users.insert_one(user_doc)
            
            if not result.inserted_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user"
                )
            
            logger.info(f"User registered successfully: {user_data.email}")
            
            # Return user without password
            user_doc["id"] = str(result.inserted_id)
            return UserResponse(**{k: v for k, v in user_doc.items() if k != "password_hash"})
            
        except (ServerSelectionTimeoutError, ConnectionFailure) as db_error:
            logger.error(f"Database error during user creation: {db_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable. Please try again."
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to server error"
        )

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """Authenticate user login with proper error handling."""
    try:
        db = await get_db_with_retry()
        
        try:
            # Find user by email
            user = await db.users.find_one({"email": login_data.email})
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Invalid email or password"
                )
            
            # Verify password
            if not verify_password(login_data.password, user["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Invalid email or password"
                )
            
            # Check if user is active
            if not user.get("is_active", True):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Account is deactivated"
                )
            
            # Update last login
            try:
                await db.users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"last_login": datetime.utcnow(), "updated_at": datetime.utcnow()}}
                )
            except Exception as update_error:
                # Log error but don't fail login
                logger.warning(f"Failed to update last login for user {user['email']}: {update_error}")
            
            # Create access token
            access_token = create_access_token(
                data={"sub": str(user["_id"]), "email": user["email"]}
            )
            
            logger.info(f"User logged in successfully: {login_data.email}")
            
            # Return token and user info
            user_response = UserResponse(
                id=str(user["_id"]),
                student_id=user["student_id"],
                email=user["email"],
                full_name=user["full_name"],
                department=user["department"],
                level=user["level"],
                phone_number=user.get("phone_number"),
                is_active=user.get("is_active", True),
                is_verified=user.get("is_verified", False)
            )
            
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=user_response
            )
            
        except (ServerSelectionTimeoutError, ConnectionFailure) as db_error:
            logger.error(f"Database error during login: {db_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable. Please try again."
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(credentials = Depends(security)):
    """Get current user information (placeholder implementation)."""
    # This is a simplified version - you'll need to implement proper token verification
    # For now, we'll return a mock response
    raise HTTPException(status_code=501, detail="Not implemented yet - use /login to get user info")

# Health check endpoint for this router
@router.get("/health")
async def auth_health_check():
    """Check if auth service and database are healthy."""
    try:
        db = await get_db_with_retry()
        # Try a simple database operation
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Auth health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
