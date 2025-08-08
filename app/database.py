import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from .core.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

def validate_mongodb_url(url: str) -> str:
    """Validate and fix MongoDB URL if needed."""
    if not url:
        print("ERROR: No MongoDB URL provided")
        return "mongodb+srv://bu22-2130:bu22-2130@cluster0.4nsgp2g.mongodb.net/babcock_smart_campus?retryWrites=true&w=majority&appName=Cluster0&ssl=true&tlsAllowInvalidCertificates=true"
    
    if not (url.startswith("mongodb://") or url.startswith("mongodb+srv://")):
        print(f"ERROR: Invalid MongoDB URL scheme: {url[:50]}...")
        return "mongodb+srv://bu22-2130:bu22-2130@cluster0.4nsgp2g.mongodb.net/babcock_smart_campus?retryWrites=true&w=majority&appName=Cluster0&ssl=true&tlsAllowInvalidCertificates=true"
    
    return url

async def connect_to_mongo():
    """Create database connection with URL validation."""
    try:
        # Validate the MongoDB URL
        mongodb_url = validate_mongodb_url(settings.MONGODB_URL)
        
        logger.info("Attempting MongoDB connection...")
        print(f"Using MongoDB URL: {mongodb_url.split('@')[0]}@{mongodb_url.split('@')[1].split('?')[0]}...")
        
        # Simple connection - let the connection string handle all SSL settings
        db.client = AsyncIOMotorClient(
            mongodb_url,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            maxPoolSize=50
        )
        
        # Test the connection
        await db.client.admin.command('ping')
        logger.info("MongoDB connection successful")
        
        # Set database
        database_name = settings.MONGODB_DATABASE or "babcock_smart_campus"
        db.database = db.client[database_name]
        logger.info(f"Connected to database: {database_name}")
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
