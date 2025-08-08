from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Class(Base):
    __tablename__ = "classes"
    
    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(20), nullable=False)
    course_title = Column(String(200), nullable=False)
    instructor = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    level = Column(String(10), nullable=False)
    room_number = Column(String(20), nullable=False)
    building = Column(String(50), nullable=False)
    day_of_week = Column(String(20), nullable=False)  # Monday, Tuesday, etc.
    start_time = Column(String(10), nullable=False)  # HH:MM format
    end_time = Column(String(10), nullable=False)    # HH:MM format
    qr_code_data = Column(String(255), unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    attendances = relationship("Attendance", back_populates="class_info")
    
    def __repr__(self):
        return f"<Class(course_code='{self.course_code}', course_title='{self.course_title}')>"

class Attendance(Base):
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    time_in = Column(DateTime, nullable=False)
    time_out = Column(DateTime)
    status = Column(String(20), default="present")  # present, late, absent
    qr_code_scanned = Column(Boolean, default=True)
    location_lat = Column(String(20))  # GPS coordinates
    location_lng = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    student = relationship("User")
    class_info = relationship("Class", back_populates="attendances")
    
    def __repr__(self):
        return f"<Attendance(student_id={self.student_id}, class_id={self.class_id}, date='{self.date}')>" 