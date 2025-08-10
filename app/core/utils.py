"""
Utility functions for date handling and data conversion
"""
from datetime import datetime
from typing import Optional, Union
from bson import ObjectId
import json

def format_datetime(dt: Optional[Union[datetime, str]]) -> Optional[str]:
    """
    Format datetime object to ISO string format
    Handles both datetime objects and string dates
    """
    if dt is None:
        return None
    
    if isinstance(dt, str):
        # If it's already a string, try to parse and reformat
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return dt  # Return as-is if we can't parse
    
    if isinstance(dt, datetime):
        return dt.isoformat()
    
    return str(dt)

def parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse date string to datetime object
    Handles various date formats safely
    """
    if not date_str:
        return None
    
    if isinstance(date_str, datetime):
        return date_str
    
    # Try different date formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try ISO format
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        pass
    
    return None

def format_object_id(obj_id: Union[ObjectId, str, None]) -> Optional[str]:
    """
    Convert ObjectId to string safely
    """
    if obj_id is None:
        return None
    
    if isinstance(obj_id, ObjectId):
        return str(obj_id)
    
    return str(obj_id)

def prepare_for_json(data: dict) -> dict:
    """
    Prepare MongoDB document for JSON serialization
    Converts ObjectIds and dates to strings
    """
    def convert_value(v):
        if isinstance(v, ObjectId):
            return str(v)
        elif isinstance(v, datetime):
            return v.isoformat()
        elif isinstance(v, dict):
            return prepare_for_json(v)
        elif isinstance(v, list):
            return [convert_value(item) for item in v]
        else:
            return v
    
    return {k: convert_value(v) for k, v in data.items()}

def safe_json_dumps(data: dict) -> str:
    """
    Safely convert data to JSON string
    Handles MongoDB-specific types
    """
    return json.dumps(prepare_for_json(data), default=str)
