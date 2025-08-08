from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from bson import ObjectId

from ..core.config import settings
from ..core.security import get_password_hash, verify_password, create_access_token
from ..database import get_database

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

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    db = get_database()
    
    # Check if user already exists
    existing_user = await db.users.find_one({"$or": [{"email": user_data.email}, {"student_id": user_data.student_id}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email or student ID already exists")
    
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
    
    result = await db.users.insert_one(user_doc)
    
    # Return user without password
    user_doc["id"] = str(result.inserted_id)
    return UserResponse(**{k: v for k, v in user_doc.items() if k != "password_hash"})

@router.post("/login", response_model=TokenResponse)
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

@router.get("/me", response_model=UserResponse)
async def get_current_user(credentials = Depends(security)):
    # This is a simplified version - you'll need to implement proper token verification
    # For now, we'll return a mock response
    raise HTTPException(status_code=501, detail="Not implemented yet - use /login to get user info") 