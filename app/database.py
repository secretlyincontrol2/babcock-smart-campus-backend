import asyncio
import logging
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.database import Database as SyncDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure
from pymongo.server_api import ServerApi
import time

from .core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages MongoDB database connections with connection pooling and retry logic"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._connection_attempts = 0
        self._max_retries = 3
        self._retry_delay = 1  # seconds
        self._is_connected = False
        self._last_health_check = 0
        self._health_check_interval = 30  # seconds
        
    async def connect(self) -> bool:
        """Establish connection to MongoDB with retry logic"""
        if self._is_connected and self.client:
            logger.info("Database already connected")
            return True
            
        for attempt in range(self._max_retries):
            try:
                logger.info(f"Attempting to connect to MongoDB (attempt {attempt + 1}/{self._max_retries})")
                
                # Create client with optimized settings
                self.client = AsyncIOMotorClient(
                    settings.MONGODB_URL,
                    server_api=ServerApi('1'),
                    maxPoolSize=50,  # Connection pool size
                    minPoolSize=10,  # Minimum connections to maintain
                    maxIdleTimeMS=30000,  # Max time connection can be idle
                    connectTimeoutMS=10000,  # Connection timeout
                    serverSelectionTimeoutMS=5000,  # Server selection timeout
                    heartbeatFrequencyMS=10000,  # Heartbeat frequency
                    retryWrites=True,
                    retryReads=True,
                    w='majority'  # Write concern
                )
                
                # Test connection
                await self.client.admin.command('ping')
                
                # Get database
                self.database = self.client[settings.MONGODB_DATABASE]
                
                # Test database access
                await self.database.command('ping')
                
                self._is_connected = True
                self._connection_attempts = 0
                logger.info(f"✅ Successfully connected to MongoDB database: {settings.MONGODB_DATABASE}")
                
                # Log connection info
                await self._log_connection_info()
                
                return True
                
            except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
                self._connection_attempts += 1
                logger.error(f"❌ MongoDB connection attempt {attempt + 1} failed: {e}")
                
                if attempt < self._max_retries - 1:
                    wait_time = self._retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"❌ Failed to connect to MongoDB after {self._max_retries} attempts")
                    self._is_connected = False
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error during MongoDB connection: {e}")
                self._is_connected = False
                return False
        
        return False
    
    async def disconnect(self):
        """Close MongoDB connection"""
        try:
            if self.client:
                self.client.close()
                logger.info("MongoDB client connection closed")
            self._is_connected = False
            self.client = None
            self.database = None
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")
    
    async def get_database(self) -> AsyncIOMotorDatabase:
        """Get database instance, ensuring connection is established"""
        if not self._is_connected or not self.database:
            await self.connect()
        
        if not self.database:
            raise ConnectionError("Failed to establish database connection")
        
        return self.database
    
    async def ensure_connection(self) -> bool:
        """Ensure database connection is active, reconnect if necessary"""
        if not self._is_connected:
            return await self.connect()
        
        try:
            # Quick ping to check if connection is still alive
            await self.client.admin.command('ping')
            return True
        except Exception:
            logger.warning("Database connection lost, attempting to reconnect...")
            return await self.connect()
    
    async def check_health(self) -> Dict[str, Any]:
        """Comprehensive health check of the database connection"""
        current_time = time.time()
        
        # Rate limit health checks
        if current_time - self._last_health_check < self._health_check_interval:
            return {
                "status": "healthy" if self._is_connected else "unhealthy",
                "cached": True,
                "last_check": self._last_health_check
            }
        
        try:
            start_time = time.time()
            
            if not self._is_connected:
                return {
                    "status": "unhealthy",
                    "message": "Not connected to database",
                    "response_time": 0,
                    "timestamp": current_time
                }
            
            # Test connection with ping
            await self.client.admin.command('ping')
            response_time = time.time() - start_time
            
            # Test database access
            await self.database.command('ping')
            
            # Get database stats
            stats = await self.database.command('dbStats')
            
            self._last_health_check = current_time
            
            return {
                "status": "healthy",
                "message": "Database is accessible",
                "response_time": f"{response_time:.3f}s",
                "timestamp": current_time,
                "stats": {
                    "collections": stats.get('collections', 0),
                    "data_size": stats.get('dataSize', 0),
                    "storage_size": stats.get('storageSize', 0),
                    "indexes": stats.get('indexes', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}",
                "response_time": 0,
                "timestamp": current_time,
                "error": str(e)
            }
    
    async def ping(self) -> bool:
        """Simple ping to check if database is accessible"""
        try:
            if not self._is_connected:
                return False
            await self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    async def _log_connection_info(self):
        """Log detailed connection information"""
        try:
            if self.client:
                # Get server info
                server_info = await self.client.admin.command('serverStatus')
                logger.info(f"Connected to MongoDB server: {server_info.get('host', 'unknown')}")
                logger.info(f"MongoDB version: {server_info.get('version', 'unknown')}")
                logger.info(f"Connection pool size: {self.client.max_pool_size}")
        except Exception as e:
            logger.warning(f"Could not log connection info: {e}")

# Global database manager instance
db_manager = DatabaseManager()

# ------------------------------
# Synchronous Database (for Flask)
# ------------------------------

class SyncDatabaseManager:
    """Synchronous MongoDB manager for Flask routes and lifecycle"""
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.database: Optional[SyncDatabase] = None
        self._is_connected: bool = False

    def connect(self) -> bool:
        try:
            if self._is_connected and self.client:
                return True
            self.client = MongoClient(settings.MONGODB_URL, server_api=ServerApi('1'))
            # Ping
            self.client.admin.command('ping')
            self.database = self.client[settings.MONGODB_DATABASE]
            self.database.command('ping')
            self._is_connected = True
            logger.info(f"✅ [SYNC] Connected to MongoDB database: {settings.MONGODB_DATABASE}")
            return True
        except Exception as e:
            logger.error(f"❌ [SYNC] MongoDB connection failed: {e}")
            self._is_connected = False
            return False

    def disconnect(self):
        try:
            if self.client:
                self.client.close()
            self.client = None
            self.database = None
            self._is_connected = False
            logger.info("[SYNC] MongoDB client connection closed")
        except Exception as e:
            logger.error(f"[SYNC] Error closing MongoDB connection: {e}")

    def get_database(self) -> SyncDatabase:
        if not self._is_connected or not self.database:
            self.connect()
        if not self.database:
            raise ConnectionError("Failed to establish database connection (sync)")
        return self.database

    def check_health(self) -> Dict[str, Any]:
        try:
            if not self._is_connected:
                return {"status": "unhealthy", "message": "Not connected"}
            self.client.admin.command('ping')
            self.database.command('ping')
            return {"status": "healthy", "database": settings.MONGODB_DATABASE}
        except Exception as e:
            return {"status": "unhealthy", "message": str(e)}

    def ping(self) -> bool:
        try:
            if not self._is_connected:
                return False
            self.client.admin.command('ping')
            return True
        except Exception:
            return False


sync_db_manager = SyncDatabaseManager()

# Convenience functions (SYNC for Flask)
def connect_to_mongo() -> bool:
    return sync_db_manager.connect()

def close_mongo_connection():
    sync_db_manager.disconnect()

def get_database():
    return sync_db_manager.get_database()

def ensure_connection() -> bool:
    return sync_db_manager.connect()

def check_database_health() -> Dict[str, Any]:
    return sync_db_manager.check_health()

def ping_database() -> bool:
    return sync_db_manager.ping()

# Async convenience functions (retained for backward compatibility)
async def connect_to_mongo_async() -> bool:
    return await db_manager.connect()

async def close_mongo_connection_async():
    await db_manager.disconnect()

async def get_database_async():
    return await db_manager.get_database()

async def ensure_connection_async() -> bool:
    return await db_manager.ensure_connection()

async def check_database_health_async() -> Dict[str, Any]:
    return await db_manager.check_health()

async def ping_database_async() -> bool:
    return await db_manager.ping()

# Database collections
def get_collection(collection_name: str):
    """Get a specific collection from the database"""
    db_sync = sync_db_manager.get_database()
    return db_sync[collection_name]

# Collection names as constants
USERS_COLLECTION = "users"
ATTENDANCE_COLLECTION = "attendance"
CAFETERIA_COLLECTION = "cafeteria"
LOCATIONS_COLLECTION = "locations"
SCHEDULES_COLLECTION = "schedules"
CHAT_COLLECTION = "chat"
MESSAGES_COLLECTION = "messages"
