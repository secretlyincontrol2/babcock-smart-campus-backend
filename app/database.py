import logging
from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure
from pymongo.server_api import ServerApi
import time

from .core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages MongoDB database connections with connection pooling and retry logic"""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.database: Optional[Database] = None
        self._connection_attempts = 0
        self._max_retries = 3
        self._retry_delay = 1  # seconds
        self._is_connected = False
        self._last_health_check = 0
        self._health_check_interval = 30  # seconds
        
    def connect(self) -> bool:
        """Establish connection to MongoDB with retry logic"""
        if self._is_connected and self.client:
            logger.info("Database already connected")
            return True
            
        for attempt in range(self._max_retries):
            try:
                logger.info(f"Attempting to connect to MongoDB (attempt {attempt + 1}/{self._max_retries})")
                
                # Create client with optimized settings
                self.client = MongoClient(
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
                self.client.admin.command('ping')
                
                # Get database
                self.database = self.client[settings.MONGODB_DATABASE]
                
                # Test database access
                self.database.command('ping')
                
                self._is_connected = True
                self._connection_attempts = 0
                logger.info(f"✅ Successfully connected to MongoDB database: {settings.MONGODB_DATABASE}")
                
                # Log connection info
                self._log_connection_info()
                
                return True
                
            except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
                self._connection_attempts += 1
                logger.error(f"❌ MongoDB connection attempt {attempt + 1} failed: {e}")
                
                if attempt < self._max_retries - 1:
                    wait_time = self._retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Failed to connect to MongoDB after {self._max_retries} attempts")
                    self._is_connected = False
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error during MongoDB connection: {e}")
                self._is_connected = False
                return False
        
        return False
    
    def disconnect(self):
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
    
    def get_database(self) -> Database:
        """Get database instance, connecting if necessary"""
        if not self._is_connected or not self.database:
            if not self.connect():
                raise ConnectionError("Failed to connect to MongoDB")
        return self.database
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        if not self._is_connected or not self.client:
            return False
        
        try:
            # Ping to check if connection is still alive
            self.client.admin.command('ping')
            return True
        except Exception:
            self._is_connected = False
            return False
    
    def check_health(self) -> Dict[str, Any]:
        """Check database health status"""
        current_time = time.time()
        
        # Only check health if enough time has passed
        if current_time - self._last_health_check < self._health_check_interval:
            return {
                "status": "healthy" if self._is_connected else "disconnected",
                "last_check": self._last_health_check,
                "connection_attempts": self._connection_attempts
            }
        
        try:
            if not self.is_connected():
                return {
                    "status": "disconnected",
                    "last_check": current_time,
                    "connection_attempts": self._connection_attempts,
                    "error": "Database not connected"
                }
            
            # Test database operations
            start_time = time.time()
            self.database.command('ping')
            ping_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Check collection count (lightweight operation)
            start_time = time.time()
            user_count = self.database.users.count_documents({})
            count_time = (time.time() - start_time) * 1000
            
            self._last_health_check = current_time
            
            return {
                "status": "healthy",
                "last_check": current_time,
                "ping_time_ms": round(ping_time, 2),
                "user_count": user_count,
                "count_time_ms": round(count_time, 2),
                "connection_attempts": self._connection_attempts,
                "database_name": settings.MONGODB_DATABASE
            }
            
        except Exception as e:
            self._last_health_check = current_time
            return {
                "status": "unhealthy",
                "last_check": current_time,
                "error": str(e),
                "connection_attempts": self._connection_attempts
            }
    
    def _log_connection_info(self):
        """Log detailed connection information"""
        try:
            if self.client and self.database:
                # Get server info
                server_info = self.client.server_info()
                
                # Get database stats
                db_stats = self.database.command('dbStats')
                
                logger.info(f"📊 MongoDB Server Version: {server_info.get('version', 'Unknown')}")
                logger.info(f"📊 Database: {settings.MONGODB_DATABASE}")
                logger.info(f"📊 Collections: {db_stats.get('collections', 0)}")
                logger.info(f"📊 Documents: {db_stats.get('objects', 0)}")
                logger.info(f"📊 Data Size: {db_stats.get('dataSize', 0) / (1024*1024):.2f} MB")
                logger.info(f"📊 Storage Size: {db_stats.get('storageSize', 0) / (1024*1024):.2f} MB")
                
        except Exception as e:
            logger.warning(f"Could not log detailed connection info: {e}")

# Global database manager instance
db_manager = DatabaseManager()

def connect_to_mongo() -> bool:
    """Connect to MongoDB"""
    return db_manager.connect()

def close_mongo_connection():
    """Close MongoDB connection"""
    db_manager.disconnect()

def get_database() -> Database:
    """Get database instance"""
    return db_manager.get_database()

def check_database_health() -> Dict[str, Any]:
    """Check database health"""
    return db_manager.check_health()

def is_database_connected() -> bool:
    """Check if database is connected"""
    return db_manager.is_connected()
