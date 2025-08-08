from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ScheduleBase(BaseModel):
    class_id: int
    day_of_week: str
    start_time: str
    end_time: str
    room_number: str
    building: str
    instructor: str
    course_code: str
    course_title: str
    notification_enabled: bool = True
    notification_minutes_before: int = 15

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleResponse(ScheduleBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True 