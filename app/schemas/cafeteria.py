from pydantic import BaseModel, Field, field_validator
from typing import Optional, Annotated, List
from datetime import datetime, time
from bson import ObjectId
from enum import Enum

class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return handler(str)

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"

class FoodCategory(str, Enum):
    MAIN_COURSE = "main_course"
    SIDE_DISH = "side_dish"
    SALAD = "salad"
    SOUP = "soup"
    DESSERT = "dessert"
    BEVERAGE = "beverage"
    FRUIT = "fruit"

class FoodItem(BaseModel):
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    name: str
    description: str
    category: FoodCategory
    price: float
    calories: Optional[int] = None
    allergens: List[str] = []
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False
    image_url: Optional[str] = None
    is_available: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class MenuDay(BaseModel):
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    date: datetime
    meal_type: MealType
    food_items: List[str]  # List of food item IDs
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CafeteriaQRCode(BaseModel):
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    user_id: str
    student_id: str
    full_name: str
    department: str
    level: str
    qr_code: str
    meal_type: MealType
    date: datetime
    is_used: bool = False
    used_at: Optional[datetime] = None
    scanned_by: Optional[str] = None  # Admin ID who scanned it
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

class QRCodeScanRequest(BaseModel):
    qr_code: str
    meal_type: MealType
    admin_id: str

class QRCodeScanResponse(BaseModel):
    success: bool
    message: str
    user_info: Optional[dict] = None
    meal_type: Optional[MealType] = None
    timestamp: Optional[datetime] = None

class CafeteriaStats(BaseModel):
    total_meals_served: int
    meals_by_type: dict
    popular_food_items: List[dict]
    daily_attendance: List[dict]
    revenue_stats: Optional[dict] = None

class FoodItemCreate(BaseModel):
    name: str
    description: str
    category: FoodCategory
    price: float
    calories: Optional[int] = None
    allergens: List[str] = []
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False
    image_url: Optional[str] = None

class FoodItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[FoodCategory] = None
    price: Optional[float] = None
    calories: Optional[int] = None
    allergens: Optional[List[str]] = None
    is_vegetarian: Optional[bool] = None
    is_vegan: Optional[bool] = None
    is_gluten_free: Optional[bool] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None

class MenuDayCreate(BaseModel):
    date: datetime
    meal_type: MealType
    food_items: List[str]

class MenuDayUpdate(BaseModel):
    food_items: Optional[List[str]] = None
    is_active: Optional[bool] = None 