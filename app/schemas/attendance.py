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

class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"
    TARDY = "tardy"

class ClassCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Class name")
    course_code: str = Field(..., min_length=3, max_length=20, description="Course code")
    department: str = Field(..., min_length=1, max_length=100, description="Department")
    level: str = Field(..., min_length=1, max_length=50, description="Academic level")
    date: datetime = Field(..., description="Class date")
    start_time: time = Field(..., description="Class start time")
    end_time: time = Field(..., description="Class end time")
    location: str = Field(..., min_length=1, max_length=200, description="Class location")
    max_students: Optional[int] = Field(None, ge=1, le=1000, description="Maximum number of students")
    description: Optional[str] = Field(None, max_length=500, description="Class description")
    
    @field_validator('end_time')
    def validate_end_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v

class ClassResponse(BaseModel):
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    name: str
    course_code: str
    instructor_id: str
    instructor_name: str
    department: str
    level: str
    date: datetime
    start_time: time
    end_time: time
    location: str
    max_students: Optional[int]
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class ClassAttendance(BaseModel):
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    user_id: str
    student_id: str
    full_name: str
    department: str
    level: str
    class_id: str
    class_name: str
    course_code: str
    date: datetime
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    status: AttendanceStatus = AttendanceStatus.PRESENT
    qr_code: str
    location: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class AttendanceCreate(BaseModel):
    class_id: str
    user_id: str
    qr_code: str
    check_in_time: Optional[datetime] = None
    location: Optional[str] = None
    notes: Optional[str] = None

class AttendanceUpdate(BaseModel):
    check_out_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    status: Optional[AttendanceStatus] = None
    notes: Optional[str] = None

class AttendanceStats(BaseModel):
    total_classes: int
    total_attendance: int
    attendance_rate: float
    attendance_by_status: dict
    attendance_by_department: dict
    attendance_by_level: dict
    weekly_attendance: List[dict]
    monthly_attendance: List[dict]
    class_performance: List[dict]

class AttendanceReport(BaseModel):
    class_id: str
    class_name: str
    course_code: str
    date: datetime
    total_students: int
    present_count: int
    absent_count: int
    late_count: int
    attendance_rate: float
    attendance_list: List[ClassAttendance]
    department_breakdown: dict
    level_breakdown: dict

class QRCodeGenerate(BaseModel):
    class_id: str
    class_name: str
    course_code: str
    instructor_id: str
    date: datetime
    start_time: time
    end_time: time
    location: str
    expires_at: datetime

class QRCodeScan(BaseModel):
    qr_code: str
    user_id: str
    timestamp: datetime
    location: Optional[str] = None

class QRCodeValidation(BaseModel):
    is_valid: bool
    message: str
    class_info: Optional[dict] = None
    expires_at: Optional[datetime] = None 