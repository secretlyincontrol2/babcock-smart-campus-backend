from motor.motor_asyncio import AsyncIOMotorClient
from .core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

async def connect_to_mongo():
    """Create database connection."""
    # Add SSL parameters to fix TLS handshake issues
    db.client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=5000,
        ssl=True,
        ssl_cert_reqs='CERT_NONE',
        tlsAllowInvalidCertificates=True
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
