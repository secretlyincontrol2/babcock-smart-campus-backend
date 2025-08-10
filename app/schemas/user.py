from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, Annotated
from datetime import datetime
from bson import ObjectId
from ..core.validators import validate_student_id, validate_phone_number

class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return handler(str)

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

class UserBase(BaseModel):
    student_id: str
    email: EmailStr
    full_name: str
    department: str
    level: str
    phone_number: Optional[str] = None
    
    @field_validator('student_id')
    @classmethod
    def validate_student_id_format(cls, v):
        if not validate_student_id(v):
            raise ValueError('Invalid student ID format. Expected: BU followed by 8 digits (e.g., BU2024001)')
        return v
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_format(cls, v):
        if v and not validate_phone_number(v):
            raise ValueError('Invalid phone number format')
        return v

class UserCreate(UserBase):
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    level: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_format(cls, v):
        if v and not validate_phone_number(v):
            raise ValueError('Invalid phone number format')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    profile_picture: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat() if v else None
        }
        populate_by_name = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None 