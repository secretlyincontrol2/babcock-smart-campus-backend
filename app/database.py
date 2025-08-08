from motor.motor_asyncio import AsyncIOMotorClient
from .core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

async def connect_to_mongo():
    """Create database connection."""
    # Simplified connection without additional SSL parameters
    # Let the connection string handle all SSL/TLS settings
    db.client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=10000
    )
    db.database = db.client[settings.MONGODB_DATABASE]
    print("Connected to MongoDB.")

async def close_mongo_connection():
    """Close database connection."""
    if db.client:
        db.client.close()
        print("Disconnected from MongoDB.")

def get_database():
    """Get database instance."""
    return db.database 
