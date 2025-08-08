import logging
import ssl
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
        return "mongodb+srv://bu22-2130:bu22-2130@ac-uyow51n-shard-00-00.4nsgp2g.mongodb.net/babcock_smart_campus?retryWrites=true&w=majority&appName=Cluster0&tls=true&tlsAllowInvalidCertificates=true"
    
    if not (url.startswith("mongodb://") or url.startswith("mongodb+srv://")):
        print(f"ERROR: Invalid MongoDB URL scheme: {url[:50]}...")
        return "mongodb+srv://bu22-2130:bu22-2130@ac-uyow51n-shard-00-00.4nsgp2g.mongodb.net/babcock_smart_campus?retryWrites=true&w=majority&appName=Cluster0&tls=true&tlsAllowInvalidCertificates=true"
    
    # Fix hostname if using old format
    if "cluster0.4nsgp2g.mongodb.net" in url:
        url = url.replace("cluster0.4nsgp2g.mongodb.net", "ac-uyow51n-shard-00-00.4nsgp2g.mongodb.net")
        print("Fixed MongoDB hostname to match Atlas cluster")
    
    return url

async def connect_to_mongo():
    """Create database connection with enhanced SSL configuration."""
    try:
        # Validate the MongoDB URL
        mongodb_url = validate_mongodb_url(settings.MONGODB_URL)
        
        logger.info("Attempting MongoDB connection...")
        print(f"Using MongoDB URL: {mongodb_url.split('@')[0]}@{mongodb_url.split('@')[1].split('?')[0]}...")
        
        # Create SSL context with relaxed settings for problematic environments
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Enhanced connection with SSL context and timeout settings
        db.client = AsyncIOMotorClient(
            mongodb_url,
            serverSelectionTimeoutMS=60000,  # Increased timeout
            connectTimeoutMS=60000,  # Increased timeout  
            socketTimeoutMS=60000,   # Increased timeout
            maxPoolSize=10,          # Reduced pool size for stability
            minPoolSize=1,
            maxIdleTimeMS=30000,
            waitQueueTimeoutMS=10000,
            ssl_context=ssl_context,  # Use custom SSL context
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            retryWrites=True,
            w='majority'
        )
        
        # Test the connection with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await db.client.admin.command('ping', maxTimeMS=30000)
                logger.info(f"MongoDB connection successful on attempt {attempt + 1}")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"Connection attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(2)
        
        # Set database
        database_name = settings.MONGODB_DATABASE or "babcock_smart_campus"
        db.database = db.client[database_name]
        logger.info(f"Connected to database: {database_name}")
        print("Connected to MongoDB successfully.")
        
        # Test database access
        collections = await db.database.list_collection_names()
        print(f"Available collections: {collections[:5] if collections else 'None found'}")
        
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        logger.error(f"MongoDB connection failed: {e}")
        print(f"Failed to connect to MongoDB: {e}")
        
        # Try alternative connection method as fallback
        await _try_fallback_connection()
        
    except Exception as e:
        logger.error(f"Unexpected MongoDB connection error: {e}")
        db.client = None
        db.database = None
        print(f"Unexpected MongoDB connection error: {e}")

async def _try_fallback_connection():
    """Try fallback connection with different SSL settings."""
    try:
        print("Trying fallback connection method...")
        
        # Simple connection without SSL context
        fallback_url = "mongodb+srv://bu22-2130:bu22-2130@ac-uyow51n-shard-00-00.4nsgp2g.mongodb.net/smart_campus_db?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"
        
        db.client = AsyncIOMotorClient(
            fallback_url,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            maxPoolSize=5
        )
        
        await db.client.admin.command('ping')
        db.database = db.client[settings.MONGODB_DATABASE or "smart_campus_db"]
        logger.info("Fallback MongoDB connection successful")
        print("Fallback connection to MongoDB successful.")
        
    except Exception as fallback_error:
        logger.error(f"Fallback connection also failed: {fallback_error}")
        db.client = None
        db.database = None
        print(f"Fallback connection failed: {fallback_error}")

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
        await db.client.admin.command('ping', maxTimeMS=10000)
        return True
    except Exception as e:
        logger.error(f"Database ping failed: {e}")
        return False

# Add asyncio import if not already present
import asyncio
