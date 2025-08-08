#!/usr/bin/env python3
"""
Test script to verify MongoDB connection
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.core.config import settings

async def test_mongodb_connection():
    """Test MongoDB connection and basic operations"""
    
    print("🔍 Testing MongoDB Connection...")
    print(f"URL: {settings.MONGODB_URL}")
    print(f"Database: {settings.MONGODB_DATABASE}")
    
    try:
        # Connect to MongoDB
        await connect_to_mongo()
        db = get_database()
        
        print("✅ Successfully connected to MongoDB!")
        
        # Test basic operations
        print("\n🧪 Testing basic operations...")
        
        # Test insert
        test_doc = {
            "test": "connection",
            "timestamp": "2024-01-01"
        }
        
        result = await db.test_collection.insert_one(test_doc)
        print(f"✅ Insert test: {result.inserted_id}")
        
        # Test find
        found_doc = await db.test_collection.find_one({"test": "connection"})
        if found_doc:
            print("✅ Find test: Document found")
        else:
            print("❌ Find test: Document not found")
        
        # Test delete
        delete_result = await db.test_collection.delete_one({"test": "connection"})
        print(f"✅ Delete test: {delete_result.deleted_count} document deleted")
        
        print("\n🎉 All MongoDB tests passed!")
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(test_mongodb_connection()) 