from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Schedule(Base):
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    day_of_week = Column(String(20), nullable=False)  # Monday, Tuesday, etc.
    start_time = Column(String(10), nullable=False)  # HH:MM format
    end_time = Column(String(10), nullable=False)    # HH:MM format
    room_number = Column(String(20), nullable=False)
    building = Column(String(50), nullable=False)
    instructor = Column(String(100), nullable=False)
    course_code = Column(String(20), nullable=False)
    course_title = Column(String(200), nullable=False)
    notification_enabled = Column(Boolean, default=True)
    notification_minutes_before = Column(Integer, default=15)  # minutes before class
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    user = relationship("User")
    class_info = relationship("Class")
    
    def __repr__(self):
        return f"<Schedule(user_id={self.user_id}, course_code='{self.course_code}', day='{self.day_of_week}')>" 