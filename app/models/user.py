from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from ..schemas.user import UserRole, UserStatus

class UserModel:
    def __init__(
        self,
        student_id: str,
        email: str,
        full_name: str,
        department: str,
        level: str,
        password_hash: str,
        phone_number: Optional[str] = None,
        role: UserRole = UserRole.STUDENT,
        status: UserStatus = UserStatus.ACTIVE,
        profile_picture: Optional[str] = None,
        is_active: bool = True,
        is_verified: bool = False,
        permissions: List[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        _id: Optional[str] = None
    ):
        self._id = _id
        self.student_id = student_id
        self.email = email
        self.full_name = full_name
        self.department = department
        self.level = level
        self.password_hash = password_hash
        self.phone_number = phone_number
        self.role = role
        self.status = status
        self.profile_picture = profile_picture
        self.is_active = is_active
        self.is_verified = is_verified
        self.permissions = permissions or []
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "_id": ObjectId(self._id) if self._id else None,
            "student_id": self.student_id,
            "email": self.email,
            "full_name": self.full_name,
            "department": self.department,
            "level": self.level,
            "password_hash": self.password_hash,
            "phone_number": self.phone_number,
            "role": self.role.value if isinstance(self.role, UserRole) else self.role,
            "status": self.status.value if isinstance(self.status, UserStatus) else self.status,
            "profile_picture": self.profile_picture,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "permissions": self.permissions,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'UserModel':
        # Safely parse dates
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = datetime.utcnow()

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except ValueError:
                updated_at = datetime.utcnow()

        return cls(
            _id=str(data.get('_id', '')),
            student_id=data.get('student_id', ''),
            email=data.get('email', ''),
            full_name=data.get('full_name', ''),
            department=data.get('department', ''),
            level=data.get('level', ''),
            password_hash=data.get('password_hash', ''),
            phone_number=data.get('phone_number'),
            role=UserRole(data.get('role', UserRole.STUDENT.value)),
            status=UserStatus(data.get('status', UserStatus.ACTIVE.value)),
            profile_picture=data.get('profile_picture'),
            is_active=data.get('is_active', True),
            is_verified=data.get('is_verified', False),
            permissions=data.get('permissions', []),
            created_at=created_at,
            updated_at=updated_at
        )

    def update(self, update_data: dict) -> None:
        """Update user fields with new data"""
        for field, value in update_data.items():
            if hasattr(self, field) and value is not None:
                setattr(self, field, value)
        self.updated_at = datetime.utcnow()

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        return permission in self.permissions

    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role"""
        return self.role == role

    def is_admin(self) -> bool:
        """Check if user is any type of admin"""
        return self.role in [UserRole.DEPARTMENT_ADMIN, UserRole.CAFETERIA_ADMIN, UserRole.SUPER_ADMIN]

    def can_manage_users(self) -> bool:
        """Check if user can manage other users"""
        return self.role in [UserRole.DEPARTMENT_ADMIN, UserRole.SUPER_ADMIN]

    def can_manage_cafeteria(self) -> bool:
        """Check if user can manage cafeteria operations"""
        return self.role in [UserRole.CAFETERIA_ADMIN, UserRole.SUPER_ADMIN]

    def to_response_dict(self) -> dict:
        """Convert to response format (without sensitive data)"""
        return {
            "_id": self._id,
            "student_id": self.student_id,
            "email": self.email,
            "full_name": self.full_name,
            "department": self.department,
            "level": self.level,
            "phone_number": self.phone_number,
            "role": self.role.value if isinstance(self.role, UserRole) else self.role,
            "status": self.status.value if isinstance(self.status, UserStatus) else self.status,
            "profile_picture": self.profile_picture,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "permissions": self.permissions,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
