"""
Custom validation functions for the application
"""
import re
from typing import Optional

def validate_email(email: str) -> bool:
    """
    Basic email validation using regex
    """
    if not email:
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_student_id(student_id: str) -> bool:
    """
    Validate Babcock University student ID format
    Expected format: BU followed by 7 digits
    Example: BU2024001
    """
    if not student_id:
        return False
    
    pattern = r'^BU\d{7}$'
    return bool(re.match(pattern, student_id))

def validate_phone_number(phone: Optional[str]) -> bool:
    """
    Validate phone number format
    Accepts Nigerian phone numbers and international format
    """
    if not phone:
        return True  # Optional field
    
    # Remove spaces, dashes, and parentheses
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Nigerian phone number patterns
    nigerian_patterns = [
        r'^\+234\d{10}$',  # +2348012345678
        r'^0\d{10}$',      # 08012345678
        r'^\+234\d{9}$',   # +234801234567
        r'^0\d{9}$',       # 0801234567
    ]
    
    for pattern in nigerian_patterns:
        if re.match(pattern, cleaned):
            return True
    
    # International format (basic)
    international_pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(international_pattern, cleaned))

def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent injection attacks
    """
    if not text:
        return ""
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '{', '}', '[', ']']
    sanitized = text
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    # Remove extra whitespace
    sanitized = ' '.join(sanitized.split())
    
    return sanitized.strip()
