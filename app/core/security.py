import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
import jwt
import logging

from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

class SecurityManager:
    """Manages security operations including JWT tokens, password hashing, and validation"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = ALGORITHM
        self.access_token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash using simple hashlib"""
        try:
            # Simple hash verification (for demo purposes)
            # In production, use proper password hashing
            return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash using simple hashlib"""
        try:
            # Simple hash generation (for demo purposes)
            # In production, use proper password hashing
            return hashlib.sha256(password.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Password hashing error: {e}")
            raise ValueError("Failed to hash password")
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token using PyJWT"""
        try:
            to_encode = data.copy()
            
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
            
            to_encode.update({"exp": expire})
            
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Access token created for user: {data.get('sub', 'unknown')}")
            
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"Token creation error: {e}")
            raise ValueError("Failed to create access token")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token using PyJWT"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired"""
        try:
            payload = self.verify_token(token)
            if not payload:
                return True
            
            exp = payload.get("exp")
            if not exp:
                return True
            
            # Convert timestamp to datetime
            exp_datetime = datetime.fromtimestamp(exp)
            return datetime.utcnow() > exp_datetime
            
        except Exception as e:
            logger.error(f"Token expiration check error: {e}")
            return True
    
    def generate_refresh_token(self, user_id: str) -> str:
        """Generate refresh token with longer expiration"""
        try:
            data = {"sub": user_id, "type": "refresh"}
            expires_delta = timedelta(days=7)  # 7 days for refresh token
            
            to_encode = data.copy()
            expire = datetime.utcnow() + expires_delta
            to_encode.update({"exp": expire})
            
            refresh_token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Refresh token created for user: {user_id}")
            
            return refresh_token
            
        except Exception as e:
            logger.error(f"Refresh token creation error: {e}")
            raise ValueError("Failed to create refresh token")
    
    def generate_password_reset_token(self, email: str) -> str:
        """Generate password reset token"""
        try:
            data = {"sub": email, "type": "password_reset"}
            expires_delta = timedelta(hours=1)  # 1 hour for password reset
            
            to_encode = data.copy()
            expire = datetime.utcnow() + expires_delta
            to_encode.update({"exp": expire})
            
            reset_token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Password reset token created for: {email}")
            
            return reset_token
            
        except Exception as e:
            logger.error(f"Password reset token creation error: {e}")
            raise ValueError("Failed to create password reset token")
    
    def verify_password_reset_token(self, token: str) -> Optional[str]:
        """Verify password reset token and return email"""
        try:
            payload = self.verify_token(token)
            if not payload:
                return None
            
            # Check if it's a password reset token
            if payload.get("type") != "password_reset":
                logger.warning("Invalid token type for password reset")
                return None
            
            email = payload.get("sub")
            if not email:
                return None
            
            return email
            
        except Exception as e:
            logger.error(f"Password reset token verification error: {e}")
            return None
    
    def generate_secure_random_string(self, length: int = 32) -> str:
        """Generate cryptographically secure random string"""
        try:
            alphabet = string.ascii_letters + string.digits
            return ''.join(secrets.choice(alphabet) for _ in range(length))
        except Exception as e:
            logger.error(f"Random string generation error: {e}")
            # Fallback to hash-based generation
            import time
            import random
            random.seed(time.time())
            return ''.join(random.choice(alphabet) for _ in range(length))
    
    def generate_api_key(self) -> str:
        """Generate API key for external integrations"""
        try:
            # Generate 64-character API key
            api_key = self.generate_secure_random_string(64)
            # Add prefix for identification
            return f"babcock_api_{api_key}"
        except Exception as e:
            logger.error(f"API key generation error: {e}")
            raise ValueError("Failed to generate API key")
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for storage"""
        try:
            return hashlib.sha256(data.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Data hashing error: {e}")
            raise ValueError("Failed to hash sensitive data")
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength"""
        try:
            errors = []
            warnings = []
            
            # Check length
            if len(password) < 8:
                errors.append("Password must be at least 8 characters long")
            elif len(password) < 12:
                warnings.append("Consider using a longer password (12+ characters)")
            
            # Check for different character types
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
            
            if not has_upper:
                errors.append("Password must contain at least one uppercase letter")
            if not has_lower:
                errors.append("Password must contain at least one lowercase letter")
            if not has_digit:
                errors.append("Password must contain at least one number")
            if not has_special:
                warnings.append("Consider adding special characters for better security")
            
            # Check for common patterns
            if password.lower() in ["password", "123456", "qwerty", "admin"]:
                errors.append("Password is too common")
            
            # Check for repeated characters
            if len(set(password)) < len(password) * 0.7:
                warnings.append("Password contains many repeated characters")
            
            is_strong = len(errors) == 0
            score = 100 - (len(errors) * 20) - (len(warnings) * 5)
            score = max(0, min(100, score))
            
            return {
                "is_strong": is_strong,
                "score": score,
                "errors": errors,
                "warnings": warnings,
                "suggestions": self._generate_password_suggestions()
            }
            
        except Exception as e:
            logger.error(f"Password strength validation error: {e}")
            return {
                "is_strong": False,
                "score": 0,
                "errors": ["Password validation failed"],
                "warnings": [],
                "suggestions": []
            }
    
    def _generate_password_suggestions(self) -> list:
        """Generate password improvement suggestions"""
        return [
            "Use a mix of uppercase and lowercase letters",
            "Include numbers and special characters",
            "Avoid common words and patterns",
            "Make it at least 12 characters long",
            "Don't use personal information",
            "Consider using a passphrase"
        ]

# Global security manager instance
security_manager = SecurityManager()

# Convenience functions for backward compatibility
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return security_manager.verify_password(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return security_manager.get_password_hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    return security_manager.create_access_token(data, expires_delta)

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
    return security_manager.verify_token(token)

def is_token_expired(token: str) -> bool:
    """Check if token is expired"""
    return security_manager.is_token_expired(token)

def generate_refresh_token(user_id: str) -> str:
    """Generate refresh token"""
    return security_manager.generate_refresh_token(user_id)

def generate_password_reset_token(email: str) -> str:
    """Generate password reset token"""
    return security_manager.generate_password_reset_token(email)

def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify password reset token"""
    return security_manager.verify_password_reset_token(token)

def generate_secure_random_string(length: int = 32) -> str:
    """Generate secure random string"""
    return security_manager.generate_secure_random_string(length)

def generate_api_key() -> str:
    """Generate API key"""
    return security_manager.generate_api_key()

def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data"""
    return security_manager.hash_sensitive_data(data)

def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength"""
    return security_manager.validate_password_strength(password) 