import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from .core.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

async def connect_to_mongo():
    """Create database connection - compatible with Motor 3.1.1."""
    try:
        logger.info("Attempting MongoDB connection...")
        
        # Simple connection - let the connection string handle all SSL settings
        # No SSL parameters in the client constructor for compatibility
        db.client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            maxPoolSize=50
        )
        
        # Test the connection
        await db.client.admin.command('ping')
        logger.info("MongoDB connection successful")
        
        # Set database using your settings
        db.database = db.client[settings.MONGODB_DATABASE]
        logger.info(f"Connected to database: {settings.MONGODB_DATABASE}")
        print("Connected to MongoDB.")
        
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        logger.error(f"MongoDB connection failed: {e}")
        db.client = None
        db.database = None
        print(f"Failed to connect to MongoDB: {e}")
        
    except Exception as e:
        logger.error(f"Unexpected MongoDB connection error: {e}")
        db.client = None
        db.database = None
        print(f"Unexpected MongoDB connection error: {e}")

async def close_mongo_connection():
    """Close database connection."""
    if db.client:
        db.client.close()
        db.client = None
        db.database = None
        logger.info("Disconnected from MongoDB.")
        print("Disconnected from MongoDB.")

def get_database():
    """Get database instance."""
    if db.database is None:
        logger.warning("Database not connected. Returning None.")
        return None
    return db.database

async def ensure_connection():
    """Ensure database connection exists, reconnect if needed."""
    if db.client is None or db.database is None:
        logger.info("Database not connected, attempting to reconnect...")
        await connect_to_mongo()
    
    if db.database is None:
        raise ConnectionFailure("Unable to establish database connection")
    
    return db.database

async def ping_database():
    """Check if database is accessible."""
    try:
        if db.client is None:
            return False
        await db.client.admin.command('ping')
        return True
    except Exception as e:
        logger.error(f"Database ping failed: {e}")
        return False
