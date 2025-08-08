from datetime import datetime
from typing import Optional
from bson import ObjectId

class PyObjectId:
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

class UserModel:
    def __init__(self, 
                 student_id: str,
                 email: str,
                 full_name: str,
                 password_hash: str,
                 department: str,
                 level: str,
                 phone_number: Optional[str] = None,
                 profile_picture: Optional[str] = None,
                 is_active: bool = True,
                 is_verified: bool = False,
                 created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None,
                 id: Optional[PyObjectId] = None):
        
        self.id = id or PyObjectId()
        self.student_id = student_id
        self.email = email
        self.full_name = full_name
        self.password_hash = password_hash
        self.department = department
        self.level = level
        self.phone_number = phone_number
        self.profile_picture = profile_picture
        self.is_active = is_active
        self.is_verified = is_verified
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self):
        return {
            "_id": self.id,
            "student_id": self.student_id,
            "email": self.email,
            "full_name": self.full_name,
            "password_hash": self.password_hash,
            "department": self.department,
            "level": self.level,
            "phone_number": self.phone_number,
            "profile_picture": self.profile_picture,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("_id"),
            student_id=data["student_id"],
            email=data["email"],
            full_name=data["full_name"],
            password_hash=data["password_hash"],
            department=data["department"],
            level=data["level"],
            phone_number=data.get("phone_number"),
            profile_picture=data.get("profile_picture"),
            is_active=data.get("is_active", True),
            is_verified=data.get("is_verified", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        ) 