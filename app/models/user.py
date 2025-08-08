from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class UserModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    student_id: str = Field(..., unique=True)
    email: str = Field(..., unique=True)
    full_name: str
    password_hash: str
    department: str
    level: str
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "student_id": "BU2024001",
                "email": "student@babcock.edu",
                "full_name": "John Doe",
                "department": "Computer Science",
                "level": "300",
                "phone_number": "+2348012345678",
                "is_active": True,
                "is_verified": True
            }
        } 