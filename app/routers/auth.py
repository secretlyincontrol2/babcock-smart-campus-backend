from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from bson import ObjectId

from ..core.config import settings
from ..core.security import get_password_hash, verify_password, create_access_token
from ..core.utils import format_datetime, format_object_id, prepare_for_json
from ..database import get_database
from ..schemas.user import UserCreate, UserLogin, UserResponse, Token

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    db = get_database()
    
    # Check if user already exists
    existing_user = await db.users.find_one({"$or": [{"email": user_data.email}, {"student_id": user_data.student_id}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email or student ID already exists")
    
    # Create user document with proper date handling
    current_time = datetime.utcnow()
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
        "created_at": current_time,
        "updated_at": current_time
    }
    
    result = await db.users.insert_one(user_doc)
    
    # Get the created user with proper ObjectId handling
    created_user = await db.users.find_one({"_id": result.inserted_id})
    
    # Convert MongoDB document to UserResponse schema with proper formatting
    return UserResponse(
        _id=format_object_id(created_user["_id"]),
        student_id=created_user["student_id"],
        email=created_user["email"],
        full_name=created_user["full_name"],
        department=created_user["department"],
        level=created_user["level"],
        phone_number=created_user.get("phone_number"),
        is_active=created_user.get("is_active", True),
        is_verified=created_user.get("is_verified", False),
        created_at=format_datetime(created_user.get("created_at")),
        updated_at=format_datetime(created_user.get("updated_at"))
    )

@router.post("/login", response_model=Token)
async def login(login_data: UserLogin):
    db = get_database()
    
    # Find user by email
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Account is deactivated")
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user["_id"]), "email": user["email"]}
    )
    
    # Return token and user info with proper date handling
    user_response = UserResponse(
        _id=format_object_id(user["_id"]),
        student_id=user["student_id"],
        email=user["email"],
        full_name=user["full_name"],
        department=user["department"],
        level=user["level"],
        phone_number=user.get("phone_number"),
        is_active=user.get("is_active", True),
        is_verified=user.get("is_verified", False),
        created_at=format_datetime(user.get("created_at")),
        updated_at=format_datetime(user.get("updated_at"))
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user(credentials = Depends(security)):
    # This is a simplified version - you'll need to implement proper token verification
    # For now, we'll return a mock response
    raise HTTPException(status_code=501, detail="Not implemented yet - use /login to get user info") 