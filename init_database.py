#!/usr/bin/env python3
"""
Script to initialize MongoDB database with collections and indexes
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.core.config import settings
from app.core.security import get_password_hash
from datetime import datetime

async def init_database():
    """Initialize the MongoDB database with collections and sample data"""
    
    print("🔧 Initializing Smart Campus Database...")
    
    # Connect to MongoDB
    await connect_to_mongo()
    db = get_database()
    
    try:
        # Create collections and indexes
        print("📊 Creating collections and indexes...")
        
        # Users collection
        await db.users.create_index("email", unique=True)
        await db.users.create_index("student_id", unique=True)
        print("✅ Users collection indexed")
        
        # Attendance collection
        await db.attendance.create_index([("user_id", 1), ("class_id", 1), ("date", 1)], unique=True)
        await db.attendance.create_index("qr_code", unique=True)
        print("✅ Attendance collection indexed")
        
        # Classes collection
        await db.classes.create_index("course_code", unique=True)
        await db.classes.create_index([("department", 1), ("level", 1)])
        print("✅ Classes collection indexed")
        
        # Cafeteria collection
        await db.cafeterias.create_index("name", unique=True)
        print("✅ Cafeterias collection indexed")
        
        # Menu items collection
        await db.menu_items.create_index([("cafeteria_id", 1), ("category", 1)])
        await db.menu_items.create_index("name")
        print("✅ Menu items collection indexed")
        
        # Schedule collection
        await db.schedules.create_index([("user_id", 1), ("day_of_week", 1), ("start_time", 1)])
        print("✅ Schedules collection indexed")
        
        # Chat rooms collection
        await db.chat_rooms.create_index("name", unique=True)
        print("✅ Chat rooms collection indexed")
        
        # Chat messages collection
        await db.chat_messages.create_index([("room_id", 1), ("created_at", -1)])
        await db.chat_messages.create_index("sender_id")
        print("✅ Chat messages collection indexed")
        
        # Locations collection
        await db.locations.create_index([("latitude", 1), ("longitude", 1)])
        await db.locations.create_index("category")
        print("✅ Locations collection indexed")
        
        # Create sample data
        print("📝 Creating sample data...")
        
        # Sample test user
        test_user = {
            "student_id": "BU2024001",
            "email": "test@babcock.edu",
            "full_name": "Test Student",
            "password_hash": get_password_hash("test123"),
            "department": "Computer Science",
            "level": "300",
            "phone_number": "+2348012345678",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Check if test user exists
        existing_user = await db.users.find_one({"email": "test@babcock.edu"})
        if not existing_user:
            await db.users.insert_one(test_user)
            print("✅ Test user created")
        else:
            print("ℹ️ Test user already exists")
        
        # Sample cafeterias
        cafeterias = [
            {
                "name": "Main Cafeteria",
                "location": "Main Campus",
                "description": "Main student cafeteria",
                "is_open": True,
                "opening_hours": "7:00 AM - 9:00 PM",
                "created_at": datetime.utcnow()
            },
            {
                "name": "Faculty Cafeteria",
                "location": "Faculty Building",
                "description": "Faculty and staff cafeteria",
                "is_open": True,
                "opening_hours": "8:00 AM - 6:00 PM",
                "created_at": datetime.utcnow()
            }
        ]
        
        for cafeteria in cafeterias:
            existing = await db.cafeterias.find_one({"name": cafeteria["name"]})
            if not existing:
                await db.cafeterias.insert_one(cafeteria)
                print(f"✅ Cafeteria '{cafeteria['name']}' created")
        
        # Sample menu items
        menu_items = [
            {
                "cafeteria_id": "Main Cafeteria",
                "name": "Jollof Rice",
                "description": "Traditional Nigerian jollof rice",
                "price": 500,
                "category": "Lunch",
                "is_vegetarian": False,
                "is_halal": True,
                "is_available": True,
                "created_at": datetime.utcnow()
            },
            {
                "cafeteria_id": "Main Cafeteria",
                "name": "Fried Rice",
                "description": "Chinese-style fried rice",
                "price": 450,
                "category": "Lunch",
                "is_vegetarian": False,
                "is_halal": True,
                "is_available": True,
                "created_at": datetime.utcnow()
            },
            {
                "cafeteria_id": "Main Cafeteria",
                "name": "Vegetable Salad",
                "description": "Fresh vegetable salad",
                "price": 300,
                "category": "Lunch",
                "is_vegetarian": True,
                "is_halal": True,
                "is_available": True,
                "created_at": datetime.utcnow()
            }
        ]
        
        for item in menu_items:
            existing = await db.menu_items.find_one({
                "cafeteria_id": item["cafeteria_id"],
                "name": item["name"]
            })
            if not existing:
                await db.menu_items.insert_one(item)
                print(f"✅ Menu item '{item['name']}' created")
        
        # Sample locations
        locations = [
            {
                "name": "Main Library",
                "category": "Academic",
                "description": "Main university library",
                "latitude": 6.5244,
                "longitude": 3.3792,
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Administrative Building",
                "category": "Administrative",
                "description": "Main administrative offices",
                "latitude": 6.5245,
                "longitude": 3.3793,
                "is_active": True,
                "created_at": datetime.utcnow()
            },
            {
                "name": "Student Center",
                "category": "Recreational",
                "description": "Student recreation center",
                "latitude": 6.5243,
                "longitude": 3.3791,
                "is_active": True,
                "created_at": datetime.utcnow()
            }
        ]
        
        for location in locations:
            existing = await db.locations.find_one({"name": location["name"]})
            if not existing:
                await db.locations.insert_one(location)
                print(f"✅ Location '{location['name']}' created")
        
        print("\n🎉 Database initialization completed successfully!")
        print("\n📋 Test Credentials:")
        print("Email: test@babcock.edu")
        print("Password: test123")
        print("Student ID: BU2024001")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(init_database()) 