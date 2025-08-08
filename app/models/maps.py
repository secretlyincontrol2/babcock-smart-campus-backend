from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.sql import func
from app.database import Base

class Location(Base):
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)  # building, cafeteria, library, etc.
    description = Column(Text)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(200))
    building_code = Column(String(20))
    floor_number = Column(Integer)
    room_number = Column(String(20))
    opening_hours = Column(String(100))  # e.g., "8:00 AM - 6:00 PM"
    contact_number = Column(String(20))
    image_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Location(name='{self.name}', category='{self.category}', lat={self.latitude}, lng={self.longitude})>" 