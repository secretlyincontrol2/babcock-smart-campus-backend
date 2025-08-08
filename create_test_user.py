#!/usr/bin/env python3
"""
Script to create a test user in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import create_engine
from app.core.config import settings

def create_test_user():
    """Create a test user in the database"""
    
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    # Create tables if they don't exist
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if test user already exists
        existing_user = db.query(User).filter(User.email == "test@babcock.edu").first()
        
        if existing_user:
            print("Test user already exists!")
            print(f"Email: {existing_user.email}")
            print(f"Password: test123")
            print(f"Student ID: {existing_user.student_id}")
            return
        
        # Create test user
        test_user = User(
            student_id="BU2024001",
            email="test@babcock.edu",
            full_name="Test Student",
            password_hash=get_password_hash("test123"),
            department="Computer Science",
            level="300",
            phone_number="+2348012345678",
            is_active=True,
            is_verified=True
        )
        
        # Add to database
        db.add(test_user)
        db.commit()
        
        print("✅ Test user created successfully!")
        print("📧 Email: test@babcock.edu")
        print("🔑 Password: test123")
        print("🆔 Student ID: BU2024001")
        print("👤 Name: Test Student")
        print("🏫 Department: Computer Science")
        print("📚 Level: 300")
        
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user() 