from pydantic import BaseModel, Field, field_validator
from typing import Optional, Annotated, List
from datetime import datetime, time, date
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

class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

class ScheduleType(str, Enum):
    REGULAR = "regular"
    EXAM = "exam"
    HOLIDAY = "holiday"
    SPECIAL = "special"
    MAKEUP = "makeup"

class ClassSchedule(BaseModel):
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    course_code: str
    course_title: str
    instructor_id: str
    instructor_name: str
    department: str
    level: str
    room_number: str
    building: str
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    schedule_type: ScheduleType = ScheduleType.REGULAR
    is_active: bool = True
    max_students: Optional[int] = None
    current_enrollment: int = 0
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ScheduleCreate(BaseModel):
    course_code: str
    course_title: str
    instructor_id: str
    department: str
    level: str
    room_number: str
    building: str
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    schedule_type: ScheduleType = ScheduleType.REGULAR
    max_students: Optional[int] = None
    description: Optional[str] = None

class ScheduleUpdate(BaseModel):
    course_title: Optional[str] = None
    instructor_id: Optional[str] = None
    room_number: Optional[str] = None
    building: Optional[str] = None
    day_of_week: Optional[DayOfWeek] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    schedule_type: Optional[ScheduleType] = None
    max_students: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class StudentSchedule(BaseModel):
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    student_id: str
    student_name: str
    department: str
    level: str
    semester: str
    academic_year: str
    courses: List[str]  # List of course IDs
    total_credit_hours: int
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ScheduleConflict(BaseModel):
    course_id: str
    course_code: str
    conflict_type: str
    conflicting_course: str
    conflict_details: str

class ScheduleStats(BaseModel):
    total_courses: int
    total_instructors: int
    total_rooms: int
    courses_by_department: dict
    courses_by_level: dict
    room_utilization: dict
    instructor_workload: dict

class TodaySchedule(BaseModel):
    date: date
    day_of_week: DayOfWeek
    classes: List[ClassSchedule]
    total_classes: int
    next_class: Optional[ClassSchedule] = None
    upcoming_classes: List[ClassSchedule]

class NextClass(BaseModel):
    course_code: str
    course_title: str
    instructor_name: str
    room_number: str
    building: str
    start_time: time
    end_time: time
    time_until_start: str
    is_ongoing: bool 