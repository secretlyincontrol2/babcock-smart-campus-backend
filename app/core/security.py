import hashlib
import secrets
import base64
from datetime import datetime, timedelta
from typing import Optional

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Simple password verification using SHA256"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def get_password_hash(password: str) -> str:
    """Simple password hashing using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Simple token creation using base64 encoding"""
    import json
    from app.core.config import settings
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire.isoformat()})
    token_data = json.dumps(to_encode)
    return base64.b64encode(token_data.encode()).decode()

def verify_token(token: str) -> dict:
    """Simple token verification"""
    import json
    try:
        token_data = base64.b64decode(token.encode()).decode()
        return json.loads(token_data)
    except:
        raise ValueError("Invalid token")

def generate_qr_code_data(student_id: str, class_id: str, timestamp: str) -> str:
    """Generate QR code data for attendance"""
    return f"attendance:{student_id}:{class_id}:{timestamp}" 