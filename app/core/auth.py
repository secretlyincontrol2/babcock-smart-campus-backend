from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from ..database import get_database
from ..core.security import verify_token
from ..models.user import UserModel
from ..core.exceptions import AuthorizationError

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token"""
    try:
        token = credentials.credentials
        payload = verify_token(token)
        email = payload.get("sub")
        
        if email is None:
            raise AuthorizationError("Invalid token")
        
        db = await get_database()
        user_data = await db.users.find_one({"email": email})
        
        if user_data is None:
            raise AuthorizationError("User not found")
        
        user = UserModel.from_dict(user_data)
        return user
        
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(current_user: UserModel = Depends(get_current_user)):
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

async def get_current_admin_user(current_user: UserModel = Depends(get_current_active_user)):
    """Get current admin user"""
    if not current_user.can_manage_users():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges"
        )
    return current_user

async def get_current_user_or_guest(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Get current user or return None for guest access"""
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except:
        return None
