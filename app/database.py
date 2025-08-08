import ssl
import certifi
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
    """Create database connection with SSL configuration for Render."""
    try:
        logger.info("Attempting MongoDB connection...")
        
        # First, try with SSL context configuration
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        try:
            # Primary connection method with SSL context
            db.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                ssl_context=ssl_context,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                maxPoolSize=50,
                retryWrites=True
            )
            
            # Test the connection
            await db.client.admin.command('ping')
            logger.info("MongoDB connection successful with SSL context")
            
        except Exception as ssl_error:
            logger.warning(f"SSL context connection failed: {ssl_error}")
            logger.info("Attempting MongoDB connection with SSL parameters...")
            
            # Fallback connection method with SSL parameters
            db.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                ssl=True,
                ssl_cert_reqs=ssl.CERT_NONE,
                ssl_match_hostname=False,
                ssl_ca_certs=certifi.where(),
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                maxPoolSize=50,
                retryWrites=True
            )
            
            # Test the connection
            await db.client.admin.command('ping')
            logger.info("MongoDB connection successful with SSL parameters")
        
        # Set database using your settings
        db.database = db.client[settings.MONGODB_DATABASE]
        logger.info(f"Connected to database: {settings.MONGODB_DATABASE}")
        print("Connected to MongoDB.")
        
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        logger.error(f"MongoDB connection failed: {e}")
        db.client = None
        db.database = None
        print(f"Failed to connect to MongoDB: {e}")
        # Don't raise here - let the app start but handle errors in endpoints
        
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
