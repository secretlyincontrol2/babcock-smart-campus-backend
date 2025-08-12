from datetime import datetime, timedelta
from typing import Optional, List
from bson import ObjectId
import secrets
import string
from ..schemas.cafeteria import MealType, FoodCategory

class FoodItemModel:
    def __init__(
        self,
        name: str,
        description: str,
        category: FoodCategory,
        price: float,
        calories: Optional[int] = None,
        allergens: List[str] = None,
        is_vegetarian: bool = False,
        is_vegan: bool = False,
        is_gluten_free: bool = False,
        image_url: Optional[str] = None,
        is_available: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        _id: Optional[str] = None
    ):
        self._id = _id
        self.name = name
        self.description = description
        self.category = category
        self.price = price
        self.calories = calories
        self.allergens = allergens or []
        self.is_vegetarian = is_vegetarian
        self.is_vegan = is_vegan
        self.is_gluten_free = is_gluten_free
        self.image_url = image_url
        self.is_available = is_available
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "_id": ObjectId(self._id) if self._id else None,
            "name": self.name,
            "description": self.description,
            "category": self.category.value if isinstance(self.category, FoodCategory) else self.category,
            "price": self.price,
            "calories": self.calories,
            "allergens": self.allergens,
            "is_vegetarian": self.is_vegetarian,
            "is_vegan": self.is_vegan,
            "is_gluten_free": self.is_gluten_free,
            "image_url": self.image_url,
            "is_available": self.is_available,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'FoodItemModel':
        return cls(
            _id=str(data.get('_id', '')),
            name=data.get('name', ''),
            description=data.get('description', ''),
            category=FoodCategory(data.get('category', FoodCategory.MAIN_COURSE.value)),
            price=data.get('price', 0.0),
            calories=data.get('calories'),
            allergens=data.get('allergens', []),
            is_vegetarian=data.get('is_vegetarian', False),
            is_vegan=data.get('is_vegan', False),
            is_gluten_free=data.get('is_gluten_free', False),
            image_url=data.get('image_url'),
            is_available=data.get('is_available', True),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

class CafeteriaQRCodeModel:
    def __init__(
        self,
        user_id: str,
        student_id: str,
        full_name: str,
        department: str,
        level: str,
        meal_type: MealType,
        date: datetime,
        qr_code: Optional[str] = None,
        is_used: bool = False,
        used_at: Optional[datetime] = None,
        scanned_by: Optional[str] = None,
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        _id: Optional[str] = None
    ):
        self._id = _id
        self.user_id = user_id
        self.student_id = student_id
        self.full_name = full_name
        self.department = department
        self.level = level
        self.meal_type = meal_type
        self.date = date
        self.qr_code = qr_code or self._generate_qr_code()
        self.is_used = is_used
        self.used_at = used_at
        self.scanned_by = scanned_by
        self.created_at = created_at or datetime.utcnow()
        self.expires_at = expires_at or (self.created_at + timedelta(hours=24))

    def _generate_qr_code(self) -> str:
        """Generate a unique QR code"""
        # Generate a unique 16-character alphanumeric code
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(16))

    def to_dict(self) -> dict:
        return {
            "_id": ObjectId(self._id) if self._id else None,
            "user_id": self.user_id,
            "student_id": self.student_id,
            "full_name": self.full_name,
            "department": self.department,
            "level": self.level,
            "meal_type": self.meal_type.value if isinstance(self.meal_type, MealType) else self.meal_type,
            "date": self.date,
            "qr_code": self.qr_code,
            "is_used": self.is_used,
            "used_at": self.used_at,
            "scanned_by": self.scanned_by,
            "created_at": self.created_at,
            "expires_at": self.expires_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CafeteriaQRCodeModel':
        return cls(
            _id=str(data.get('_id', '')),
            user_id=data.get('user_id', ''),
            student_id=data.get('student_id', ''),
            full_name=data.get('full_name', ''),
            department=data.get('department', ''),
            level=data.get('level', ''),
            meal_type=MealType(data.get('meal_type', MealType.BREAKFAST.value)),
            date=data.get('date'),
            qr_code=data.get('qr_code'),
            is_used=data.get('is_used', False),
            used_at=data.get('used_at'),
            scanned_by=data.get('scanned_by'),
            created_at=data.get('created_at'),
            expires_at=data.get('expires_at')
        )

    def mark_as_used(self, admin_id: str) -> None:
        """Mark QR code as used by admin"""
        self.is_used = True
        self.used_at = datetime.utcnow()
        self.scanned_by = admin_id

    def is_expired(self) -> bool:
        """Check if QR code has expired"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if QR code is valid for use"""
        return not self.is_used and not self.is_expired()

class MenuDayModel:
    def __init__(
        self,
        date: datetime,
        meal_type: MealType,
        food_items: List[str],
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        _id: Optional[str] = None
    ):
        self._id = _id
        self.date = date
        self.meal_type = meal_type
        self.food_items = food_items
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "_id": ObjectId(self._id) if self._id else None,
            "date": self.date,
            "meal_type": self.meal_type.value if isinstance(self.meal_type, MealType) else self.meal_type,
            "food_items": self.food_items,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MenuDayModel':
        return cls(
            _id=str(data.get('_id', '')),
            date=data.get('date'),
            meal_type=MealType(data.get('meal_type', MealType.BREAKFAST.value)),
            food_items=data.get('food_items', []),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    def add_food_item(self, food_item_id: str) -> None:
        """Add a food item to the menu"""
        if food_item_id not in self.food_items:
            self.food_items.append(food_item_id)
            self.updated_at = datetime.utcnow()

    def remove_food_item(self, food_item_id: str) -> None:
        """Remove a food item from the menu"""
        if food_item_id in self.food_items:
            self.food_items.remove(food_item_id)
            self.updated_at = datetime.utcnow()

    def toggle_active(self) -> None:
        """Toggle menu active status"""
        self.is_active = not self.is_active
        self.updated_at = datetime.utcnow() 