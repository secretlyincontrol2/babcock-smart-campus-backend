from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Cafeteria(Base):
    __tablename__ = "cafeterias"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(200), nullable=False)
    building = Column(String(50), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    opening_time = Column(String(10), nullable=False)  # HH:MM format
    closing_time = Column(String(10), nullable=False)  # HH:MM format
    is_open = Column(Boolean, default=True)
    description = Column(Text)
    image_url = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    menu_items = relationship("MenuItem", back_populates="cafeteria")
    
    def __repr__(self):
        return f"<Cafeteria(name='{self.name}', location='{self.location}')>"

class MenuItem(Base):
    __tablename__ = "menu_items"
    
    id = Column(Integer, primary_key=True, index=True)
    cafeteria_id = Column(Integer, ForeignKey("cafeterias.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)  # breakfast, lunch, dinner, snacks
    is_available = Column(Boolean, default=True)
    is_vegetarian = Column(Boolean, default=False)
    is_halal = Column(Boolean, default=False)
    image_url = Column(String(255))
    preparation_time = Column(Integer)  # in minutes
    calories = Column(Integer)
    allergens = Column(Text)  # comma-separated allergens
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    cafeteria = relationship("Cafeteria", back_populates="menu_items")
    
    def __repr__(self):
        return f"<MenuItem(name='{self.name}', price={self.price}, category='{self.category}')>" 