#!/usr/bin/env python3
"""
Test MongoDB connection locally to diagnose SSL handshake issues
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection strings to test
CONNECTION_STRINGS = [
    # Current connection string
    "mongodb+srv://bu22-2130:bu22-2130@cluster0.4nsgp2g.mongodb.net/smart_campus_db?retryWrites=true&w=majority",
    
    # Alternative with appName
    "mongodb+srv://bu22-2130:bu22-2130@cluster0.4nsgp2g.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
    
    # Basic connection string
    "mongodb+srv://bu22-2130:bu22-2130@cluster0.4nsgp2g.mongodb.net/",
    
    # With explicit SSL parameters
    "mongodb+srv://bu22-2130:bu22-2130@cluster0.4nsgp2g.mongodb.net/?retryWrites=true&w=majority&ssl=true",
]

async def test_connection(connection_string, test_name):
    """Test a MongoDB connection string"""
    print(f"\n🔍 Testing: {test_name}")
    print(f"Connection string: {connection_string}")
    
    try:
        # Try with timeout settings
        client = AsyncIOMotorClient(
            connection_string,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000
        )
        
        # Test the connection
        await client.admin.command('ping')
        print("✅ Connection successful!")
        
        # List databases
        databases = await client.list_database_names()
        print(f"📊 Available databases: {databases}")
        
        # Test specific database
        db = client.smart_campus_db
        collections = await db.list_collection_names()
        print(f"📁 Collections in smart_campus_db: {collections}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 MongoDB Connection Test")
    print("=" * 50)
    
    # Test each connection string
    results = []
    for i, conn_str in enumerate(CONNECTION_STRINGS, 1):
        success = await test_connection(conn_str, f"Test {i}")
        results.append((i, success))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    for test_num, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"Test {test_num}: {status}")
    
    # Check if any test passed
    if any(success for _, success in results):
        print("\n🎉 At least one connection method works!")
    else:
        print("\n⚠️  All connection methods failed. Possible issues:")
        print("   - MongoDB Atlas cluster is down")
        print("   - Network access restrictions")
        print("   - Credentials are incorrect")
        print("   - IP whitelist restrictions")

if __name__ == "__main__":
    asyncio.run(main())
