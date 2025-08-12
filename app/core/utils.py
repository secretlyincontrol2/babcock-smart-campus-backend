"""
Utility functions for date handling and data conversion
"""
import hashlib
import secrets
import string
import re
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union, Tuple
from bson import ObjectId
import logging
import math
from functools import wraps
import time

# Configure logging
logger = logging.getLogger(__name__)

class DataUtils:
    """Utility class for data manipulation and validation"""
    
    @staticmethod
    def generate_id() -> str:
        """Generate a unique ID"""
        return str(ObjectId())
    
    @staticmethod
    def is_valid_object_id(id_string: str) -> bool:
        """Check if a string is a valid ObjectId"""
        try:
            ObjectId(id_string)
            return True
        except Exception:
            return False
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """Sanitize and truncate string input"""
        if not text:
            return ""
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', text.strip())
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."
        
        return sanitized
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        return len(digits_only) >= 10 and len(digits_only) <= 15
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, List[str]]:
        """Validate password strength"""
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def hash_data(data: str) -> str:
        """Hash data using SHA-256"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
        """Mask sensitive data like credit cards or phone numbers"""
        if len(data) <= visible_chars * 2:
            return "*" * len(data)
        
        return data[:visible_chars] + "*" * (len(data) - visible_chars * 2) + data[-visible_chars:]

class DateTimeUtils:
    """Utility class for date and time operations"""
    
    @staticmethod
    def get_current_timestamp() -> datetime:
        """Get current UTC timestamp"""
        return datetime.now(timezone.utc)
    
    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format datetime to string"""
        return dt.strftime(format_str)
    
    @staticmethod
    def parse_datetime(date_string: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
        """Parse string to datetime"""
        try:
            return datetime.strptime(date_string, format_str)
        except ValueError:
            return None
    
    @staticmethod
    def is_expired(timestamp: datetime, expiry_minutes: int = 30) -> bool:
        """Check if a timestamp has expired"""
        expiry_time = timestamp + timedelta(minutes=expiry_minutes)
        return datetime.now(timezone.utc) > expiry_time
    
    @staticmethod
    def get_time_until_expiry(timestamp: datetime, expiry_minutes: int = 30) -> timedelta:
        """Get time remaining until expiry"""
        expiry_time = timestamp + timedelta(minutes=expiry_minutes)
        return expiry_time - datetime.now(timezone.utc)
    
    @staticmethod
    def is_business_hours(current_time: Optional[datetime] = None) -> bool:
        """Check if current time is within business hours (8 AM - 6 PM)"""
        if current_time is None:
            current_time = datetime.now()
        
        return 8 <= current_time.hour < 18
    
    @staticmethod
    def get_week_range(date: datetime) -> Tuple[datetime, datetime]:
        """Get start and end of week for a given date"""
        start = date - timedelta(days=date.weekday())
        end = start + timedelta(days=6)
        return start, end

class LocationUtils:
    """Utility class for location and coordinate operations"""
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    @staticmethod
    def is_within_radius(lat1: float, lon1: float, lat2: float, lon2: float, radius_km: float) -> bool:
        """Check if two points are within a specified radius"""
        distance = LocationUtils.calculate_distance(lat1, lon1, lat2, lon2)
        return distance <= radius_km
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> bool:
        """Validate latitude and longitude values"""
        return -90 <= lat <= 90 and -180 <= lon <= 180
    
    @staticmethod
    def get_bounding_box(center_lat: float, center_lon: float, radius_km: float) -> Dict[str, float]:
        """Get bounding box for a circular area"""
        # Approximate bounding box (simplified)
        lat_delta = radius_km / 111.32  # 1 degree latitude ≈ 111.32 km
        lon_delta = radius_km / (111.32 * math.cos(math.radians(center_lat)))
        
        return {
            "min_lat": center_lat - lat_delta,
            "max_lat": center_lat + lat_delta,
            "min_lon": center_lon - lon_delta,
            "max_lon": center_lon + lon_delta
        }

class RateLimitUtils:
    """Utility class for rate limiting operations"""
    
    _rate_limit_store: Dict[str, List[float]] = {}
    
    @staticmethod
    def check_rate_limit(key: str, max_requests: int, window_minutes: int) -> bool:
        """Check if rate limit is exceeded"""
        current_time = time.time()
        window_seconds = window_minutes * 60
        
        # Initialize or clean old entries
        if key not in RateLimitUtils._rate_limit_store:
            RateLimitUtils._rate_limit_store[key] = []
        
        # Remove old entries outside the window
        RateLimitUtils._rate_limit_store[key] = [
            timestamp for timestamp in RateLimitUtils._rate_limit_store[key]
            if current_time - timestamp < window_seconds
        ]
        
        # Check if limit exceeded
        if len(RateLimitUtils._rate_limit_store[key]) >= max_requests:
            return False
        
        # Add current request
        RateLimitUtils._rate_limit_store[key].append(current_time)
        return True
    
    @staticmethod
    def get_remaining_requests(key: str, max_requests: int, window_minutes: int) -> int:
        """Get remaining requests for a key"""
        current_time = time.time()
        window_seconds = window_minutes * 60
        
        if key not in RateLimitUtils._rate_limit_store:
            return max_requests
        
        # Count requests within window
        recent_requests = len([
            timestamp for timestamp in RateLimitUtils._rate_limit_store[key]
            if current_time - timestamp < window_seconds
        ])
        
        return max(0, max_requests - recent_requests)
    
    @staticmethod
    def get_reset_time(key: str, window_minutes: int) -> Optional[float]:
        """Get time when rate limit resets for a key"""
        if key not in RateLimitUtils._rate_limit_store or not RateLimitUtils._rate_limit_store[key]:
            return None
        
        # Find oldest request in current window
        oldest_request = min(RateLimitUtils._rate_limit_store[key])
        return oldest_request + (window_minutes * 60)

class AsyncUtils:
    """Utility class for async operations"""
    
    @staticmethod
    def retry_async(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
        """Decorator for retrying async functions"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_retries):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries - 1:
                            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                            await asyncio.sleep(current_delay)
                            current_delay *= backoff
                        else:
                            logger.error(f"All {max_retries} attempts failed. Last error: {e}")
                
                raise last_exception
            return wrapper
        return decorator
    
    @staticmethod
    async def timeout_handler(coro, timeout_seconds: float):
        """Execute coroutine with timeout"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.error(f"Operation timed out after {timeout_seconds} seconds")
            raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
    
    @staticmethod
    async def batch_process(items: List[Any], processor_func, batch_size: int = 10, max_concurrent: int = 5):
        """Process items in batches with concurrency control"""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # Process batch with concurrency limit
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_item(item):
                async with semaphore:
                    return await processor_func(item)
            
            batch_results = await asyncio.gather(*[process_item(item) for item in batch])
            results.extend(batch_results)
        
        return results

class ValidationUtils:
    """Utility class for data validation"""
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """Validate that required fields are present and not empty"""
        missing_fields = []
        
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing_fields.append(field)
        
        return missing_fields
    
    @staticmethod
    def validate_field_types(data: Dict[str, Any], field_types: Dict[str, type]) -> List[str]:
        """Validate field types"""
        type_errors = []
        
        for field, expected_type in field_types.items():
            if field in data and not isinstance(data[field], expected_type):
                type_errors.append(f"Field '{field}' must be of type {expected_type.__name__}")
        
        return type_errors
    
    @staticmethod
    def validate_string_length(data: Dict[str, Any], field_lengths: Dict[str, Tuple[int, int]]) -> List[str]:
        """Validate string field lengths"""
        length_errors = []
        
        for field, (min_length, max_length) in field_lengths.items():
            if field in data and isinstance(data[field], str):
                if len(data[field]) < min_length:
                    length_errors.append(f"Field '{field}' must be at least {min_length} characters")
                elif len(data[field]) > max_length:
                    length_errors.append(f"Field '{field}' must be at most {max_length} characters")
        
        return length_errors
    
    @staticmethod
    def validate_numeric_range(data: Dict[str, Any], field_ranges: Dict[str, Tuple[float, float]]) -> List[str]:
        """Validate numeric field ranges"""
        range_errors = []
        
        for field, (min_value, max_value) in field_ranges.items():
            if field in data and isinstance(data[field], (int, float)):
                if data[field] < min_value or data[field] > max_value:
                    range_errors.append(f"Field '{field}' must be between {min_value} and {max_value}")
        
        return range_errors

# Convenience functions for backward compatibility
def generate_id() -> str:
    """Generate a unique ID"""
    return DataUtils.generate_id()

def is_valid_object_id(id_string: str) -> bool:
    """Check if a string is a valid ObjectId"""
    return DataUtils.is_valid_object_id(id_string)

def sanitize_string(text: str, max_length: int = 1000) -> str:
    """Sanitize and truncate string input"""
    return DataUtils.sanitize_string(text, max_length)

def validate_email(email: str) -> bool:
    """Validate email format"""
    return DataUtils.validate_email(email)

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    return DataUtils.validate_phone(phone)

def validate_password(password: str) -> Tuple[bool, List[str]]:
    """Validate password strength"""
    return DataUtils.validate_password(password)

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    return DataUtils.generate_secure_token(length)

def hash_data(data: str) -> str:
    """Hash data using SHA-256"""
    return DataUtils.hash_data(data)

def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive data like credit cards or phone numbers"""
    return DataUtils.mask_sensitive_data(data, visible_chars)

def get_current_timestamp() -> datetime:
    """Get current UTC timestamp"""
    return DateTimeUtils.get_current_timestamp()

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string"""
    return DateTimeUtils.format_datetime(dt, format_str)

def parse_datetime(date_string: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """Parse string to datetime"""
    return DateTimeUtils.parse_datetime(date_string, format_str)

def is_expired(timestamp: datetime, expiry_minutes: int = 30) -> bool:
    """Check if a timestamp has expired"""
    return DateTimeUtils.is_expired(timestamp, expiry_minutes)

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula"""
    return LocationUtils.calculate_distance(lat1, lon1, lat2, lon2)

def is_within_radius(lat1: float, lon1: float, lat2: float, lon2: float, radius_km: float) -> bool:
    """Check if two points are within a specified radius"""
    return LocationUtils.is_within_radius(lat1, lon1, lat2, lon2, radius_km)

def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate latitude and longitude values"""
    return LocationUtils.validate_coordinates(lat, lon)

def check_rate_limit(key: str, max_requests: int, window_minutes: int) -> bool:
    """Check if rate limit is exceeded"""
    return RateLimitUtils.check_rate_limit(key, max_requests, window_minutes)

def get_remaining_requests(key: str, max_requests: int, window_minutes: int) -> int:
    """Get remaining requests for a key"""
    return RateLimitUtils.get_remaining_requests(key, max_requests, window_minutes)

def get_reset_time(key: str, window_minutes: int) -> Optional[float]:
    """Get time when rate limit resets for a key"""
    return RateLimitUtils.get_reset_time(key, window_minutes)

def retry_async(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying async functions"""
    return AsyncUtils.retry_async(max_retries, delay, backoff)

async def timeout_handler(coro, timeout_seconds: float):
    """Execute coroutine with timeout"""
    return await AsyncUtils.timeout_handler(coro, timeout_seconds)

async def batch_process(items: List[Any], processor_func, batch_size: int = 10, max_concurrent: int = 5):
    """Process items in batches with concurrency control"""
    return await AsyncUtils.batch_process(items, processor_func, batch_size, max_concurrent)

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """Validate that required fields are present and not empty"""
    return ValidationUtils.validate_required_fields(data, required_fields)

def validate_field_types(data: Dict[str, Any], field_types: Dict[str, type]) -> List[str]:
    """Validate field types"""
    return ValidationUtils.validate_field_types(data, field_types)

def validate_string_length(data: Dict[str, Any], field_lengths: Dict[str, Tuple[int, int]]) -> List[str]:
    """Validate string field lengths"""
    return ValidationUtils.validate_string_length(data, field_lengths)

def validate_numeric_range(data: Dict[str, Any], field_ranges: Dict[str, Tuple[float, float]]) -> List[str]:
    """Validate numeric field ranges"""
    return ValidationUtils.validate_numeric_range(data, field_ranges)

def format_object_id(obj_id: Union[str, ObjectId]) -> str:
    """Format ObjectId to string"""
    if isinstance(obj_id, ObjectId):
        return str(obj_id)
    return str(obj_id)

def validate_object_id(obj_id: Union[str, ObjectId]) -> bool:
    """Validate if an ObjectId is valid"""
    try:
        if isinstance(obj_id, ObjectId):
            return True
        ObjectId(obj_id)
        return True
    except Exception:
        return False
