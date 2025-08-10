#!/usr/bin/env python3
"""
Test FastAPI backend locally to verify it works
"""

import asyncio
import uvicorn
from app.main import app
from app.database import connect_to_mongo, close_mongo_connection

async def test_backend():
    """Test the backend locally"""
    print("🚀 Testing FastAPI Backend Locally")
    print("=" * 50)
    
    try:
        # Connect to MongoDB
        print("📡 Connecting to MongoDB...")
        await connect_to_mongo()
        print("✅ MongoDB connected successfully!")
        
        # Test database operations
        from app.database import get_database
        db = get_database()
        
        # Test users collection
        users_count = await db.users.count_documents({})
        print(f"👥 Users in database: {users_count}")
        
        # Test attendance collection
        attendance_count = await db.attendance.count_documents({})
        print(f"📊 Attendance records: {attendance_count}")
        
        print("\n✅ Backend is working correctly!")
        print("🌐 You can now test the API endpoints:")
        print("   - http://localhost:8000/")
        print("   - http://localhost:8000/health")
        print("   - http://localhost:8000/docs")
        
        return True
        
    except Exception as e:
        print(f"❌ Backend test failed: {type(e).__name__}: {e}")
        return False
    finally:
        await close_mongo_connection()

def run_backend():
    """Run the FastAPI backend locally"""
    print("🚀 Starting FastAPI Backend...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    # Test the backend first
    success = asyncio.run(test_backend())
    
    if success:
        print("\n🎉 Backend test passed! Starting server...")
        run_backend()
    else:
        print("\n❌ Backend test failed! Check the errors above.")
