#!/usr/bin/env python3
"""
Script to create a test user in MongoDB for Flask backend
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import connect_to_mongo, get_database
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_test_user():
    """Create a test user in MongoDB"""
    
    try:
        # Connect to MongoDB
        connect_to_mongo()
        db = get_database()
        
        # Check if test user already exists
        existing_user = db.users.find_one({"email": "test@babcock.edu"})
        
        if existing_user:
            print("✅ Test user already exists!")
            print(f"📧 Email: {existing_user['email']}")
            print(f"🔑 Password: test123")
            print(f"🆔 Student ID: {existing_user['student_id']}")
            print(f"👤 Name: {existing_user['full_name']}")
            return
        
        # Create test user
        test_user = {
            "student_id": "BU2024001",
            "email": "test@babcock.edu",
            "full_name": "Test Student",
            "password_hash": generate_password_hash("test123"),
            "department": "Computer Science",
            "level": "300",
            "phone_number": "+2348012345678",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Add to database
        result = db.users.insert_one(test_user)
        test_user['_id'] = str(result.inserted_id)
        
        print("✅ Test user created successfully!")
        print("📧 Email: test@babcock.edu")
        print("🔑 Password: test123")
        print("🆔 Student ID: BU2024001")
        print("👤 Name: Test Student")
        print("🏫 Department: Computer Science")
        print("📚 Level: 300")
        print(f"🆔 MongoDB ID: {result.inserted_id}")
        
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_test_user()
