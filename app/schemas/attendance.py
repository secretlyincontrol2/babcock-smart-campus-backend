from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ClassBase(BaseModel):
    course_code: str
    course_title: str
    instructor: str
    department: str
    level: str
    room_number: str
    building: str
    day_of_week: str
    start_time: str
    end_time: str

class ClassCreate(ClassBase):
    pass

class ClassResponse(ClassBase):
    id: int
    qr_code_data: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class AttendanceBase(BaseModel):
    class_id: int
    date: datetime
    time_in: datetime
    status: str = "present"

class AttendanceCreate(AttendanceBase):
    pass

class AttendanceResponse(AttendanceBase):
    id: int
    student_id: int
    time_out: Optional[datetime] = None
    qr_code_scanned: bool
    location_lat: Optional[str] = None
    location_lng: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True 