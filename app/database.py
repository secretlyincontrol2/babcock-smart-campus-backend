from motor.motor_asyncio import AsyncIOMotorClient
from .core.config import settings
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database = None
    is_connected: bool = False

db = Database()

async def connect_to_mongo():
    """Create database connection with retry logic."""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting MongoDB connection (attempt {attempt + 1}/{max_retries})")
            
            # Connection options for better reliability
            connection_options = {
                'serverSelectionTimeoutMS': 30000,  # Increased timeout
                'connectTimeoutMS': 30000,
                'socketTimeoutMS': 30000,
                'maxPoolSize': 10,
                'minPoolSize': 1,
                'maxIdleTimeMS': 30000,
                'retryWrites': True,
                'w': 'majority'
            }
            
            db.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                **connection_options
            )
            
            # Test the connection
            await db.client.admin.command('ping')
            db.database = db.client[settings.MONGODB_DATABASE]
            db.is_connected = True
            
            logger.info("✅ Connected to MongoDB successfully!")
            return
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("All connection attempts failed. Database service unavailable.")
                db.is_connected = False
                raise Exception("Database service is temporarily unavailable")

async def close_mongo_connection():
    """Close database connection."""
    if db.client:
        db.client.close()
        db.is_connected = False
        logger.info("Disconnected from MongoDB.")

def get_database():
    """Get database instance."""
    if not db.is_connected:
        raise Exception("Database not connected. Please ensure the connection is established.")
    return db.database

async def check_database_health():
    """Check if database connection is healthy."""
    try:
        if db.client and db.is_connected:
            await db.client.admin.command('ping')
            return True
        return False
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db.is_connected = False
        return False 