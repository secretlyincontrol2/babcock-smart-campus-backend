from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import List, Optional
import jwt
from passlib.context import CryptContext
from bson import ObjectId

from ..database import get_database
from ..schemas.user import (
    UserCreate, UserResponse, UserLogin, Token, TokenData, 
    AdminCreate, AdminUpdate, UserUpdate, UserRole, UserStatus
)
from ..models.user import UserModel
from ..core.utils import format_datetime, format_object_id
from ..core.security import (
    create_access_token, get_password_hash, verify_password
)
from ..core.auth import get_current_user, get_current_active_user
from ..core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, background_tasks: BackgroundTasks):
    """Register a new user"""
    db = get_database()
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if student ID already exists
    existing_student = await db.users.find_one({"student_id": user_data.student_id})
    if existing_student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student ID already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user model
    user = UserModel(
        student_id=user_data.student_id,
        email=user_data.email,
        full_name=user_data.full_name,
        department=user_data.department,
        level=user_data.level,
        password_hash=hashed_password,
        phone_number=user_data.phone_number,
        role=user_data.role,
        status=user_data.status
    )
    
    # Insert into database
    result = await db.users.insert_one(user.to_dict())
    user._id = str(result.inserted_id)
    
    # Get created user for response
    created_user = await db.users.find_one({"_id": result.inserted_id})
    user_response = UserModel.from_dict(created_user)
    
    # Background task: Send welcome email
    background_tasks.add_task(send_welcome_email, user_response.email, user_response.full_name)
    
    return user_response.to_response_dict()

@router.post("/login", response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login user and return access token"""
    db = get_database()
    
    # Find user by email
    user_data = await db.users.find_one({"email": form_data.username})
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    user = UserModel.from_dict(user_data)
    
    # Verify password
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value, "permissions": user.permissions},
        expires_delta=access_token_expires
    )
    
    # Update last login
    await db.users.update_one(
        {"_id": ObjectId(user._id)},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user.to_response_dict(),
        "permissions": user.permissions
    }

@router.post("/admin/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_admin(
    admin_data: AdminCreate, 
    current_user: UserModel = Depends(get_current_active_user)
):
    """Register a new admin (requires existing admin privileges)"""
    # Check if current user can create admins
    if not current_user.can_manage_users():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to create admin accounts"
        )
    
    db = get_database()
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": admin_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(admin_data.password)
    
    # Create admin user
    admin = UserModel(
        student_id=f"ADMIN_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        email=admin_data.email,
        full_name=admin_data.full_name,
        department=admin_data.department,
        password_hash=hashed_password,
        level="ADMIN",
        role=admin_data.role,
        phone_number=admin_data.phone_number,
        permissions=get_default_permissions(admin_data.role)
    )
    
    # Insert into database
    result = await db.users.insert_one(admin.to_dict())
    admin._id = str(result.inserted_id)
    
    return admin.to_response_dict()

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserModel = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user.to_response_dict()

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Update current user information"""
    db = get_database()
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    if update_data:
        current_user.update(update_data)
        
        # Update in database
        await db.users.update_one(
            {"_id": ObjectId(current_user._id)},
            {"$set": current_user.to_dict()}
        )
    
    return current_user.to_response_dict()

@router.put("/admin/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: AdminUpdate,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Update user (admin only)"""
    if not current_user.can_manage_users():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges"
        )
    
    db = get_database()
    
    # Find user to update
    user_data = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = UserModel.from_dict(user_data)
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    if update_data:
        user.update(update_data)
        
        # Update in database
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": user.to_dict()}
        )
    
    return user.to_response_dict()

@router.get("/users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    department: Optional[str] = None,
    role: Optional[UserRole] = None,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get users with filtering (admin only)"""
    if not current_user.can_manage_users():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges"
        )
    
    db = get_database()
    
    # Build filter
    filter_query = {}
    if department:
        filter_query["department"] = department
    if role:
        filter_query["role"] = role.value
    
    # Get users
    cursor = db.users.find(filter_query).skip(skip).limit(limit)
    users = []
    async for user_data in cursor:
        user = UserModel.from_dict(user_data)
        users.append(user.to_response_dict())
    
    return users

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """Delete user (super admin only)"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can delete users"
        )
    
    db = get_database()
    
    # Check if user exists
    user_data = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Soft delete (mark as inactive)
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": False, "status": UserStatus.INACTIVE.value}}
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: UserModel = Depends(get_current_active_user)):
    """Refresh access token"""
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.email, "role": current_user.role.value, "permissions": current_user.permissions},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": current_user.to_response_dict(),
        "permissions": current_user.permissions
    }

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout_user(current_user: UserModel = Depends(get_current_active_user)):
    """Logout user (invalidate token)"""
    # In a real implementation, you would add the token to a blacklist
    # For now, we'll just return success
    return {"message": "Successfully logged out"}

# Helper functions
def get_default_permissions(role: UserRole) -> List[str]:
    """Get default permissions for a role"""
    permissions = {
        UserRole.STUDENT: ["read_own_profile", "update_own_profile"],
        UserRole.DEPARTMENT_ADMIN: [
            "read_own_profile", "update_own_profile",
            "manage_department_users", "view_department_stats",
            "manage_department_schedule", "manage_department_attendance"
        ],
        UserRole.CAFETERIA_ADMIN: [
            "read_own_profile", "update_own_profile",
            "manage_cafeteria_menu", "scan_qr_codes",
            "view_cafeteria_stats", "manage_food_items"
        ],
        UserRole.SUPER_ADMIN: [
            "read_own_profile", "update_own_profile",
            "manage_all_users", "manage_all_departments",
            "manage_cafeteria", "view_all_stats",
            "system_configuration"
        ]
    }
    return permissions.get(role, [])

async def send_welcome_email(email: str, full_name: str):
    """Send welcome email to new user (background task)"""
    # In a real implementation, you would send an actual email
    # For now, we'll just log it
    print(f"Sending welcome email to {email} for {full_name}") 
