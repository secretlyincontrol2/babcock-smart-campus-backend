from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import logging
import time
from typing import Dict, Any

from .core.config import settings
from .database import connect_to_mongo, close_mongo_connection, check_database_health
from .routers import auth, users, attendance, cafeteria, maps, schedule, chat
from .core.exceptions import CustomHTTPException

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    startup_time = time.time()
    try:
        logger.info("🚀 Starting Smart Campus App...")
        # Try to connect to MongoDB but don't fail if it doesn't work
        if not settings.DEMO_MODE:
            try:
                await connect_to_mongo()
                logger.info("✅ MongoDB connection established")
            except Exception as e:
                logger.warning(f"⚠️ MongoDB connection failed (continuing without database): {e}")
                logger.info("📝 Running in offline/demo mode - some features may be limited")
        else:
            logger.info("🎭 Running in DEMO MODE - MongoDB connection skipped")
            logger.info("📝 Demo mode enabled - using mock data and limited features")
        
        startup_duration = time.time() - startup_time
        logger.info(f"✅ Application startup completed successfully in {startup_duration:.2f}s")
    except Exception as e:
        startup_duration = time.time() - startup_time
        logger.error(f"❌ Application startup failed after {startup_duration:.2f}s: {e}")
        # Don't raise here, let the app start but mark database as unavailable
    
    yield
    
    # Shutdown
    try:
        await close_mongo_connection()
        logger.info("🔄 Application shutdown completed")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Smart Campus App API for Babcock University - Modern, Secure, and Scalable",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# Security middleware
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure with specific hosts in production
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Global exception handler
@app.exception_handler(CustomHTTPException)
async def custom_http_exception_handler(request: Request, exc: CustomHTTPException):
    """Handle custom HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "type": exc.error_type,
            "timestamp": time.time(),
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unexpected errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "type": "internal_error",
            "timestamp": time.time(),
            "path": request.url.path
        }
    )

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
app.include_router(cafeteria.router, prefix="/cafeteria", tags=["Cafeteria"])
app.include_router(maps.router, prefix="/maps", tags=["Maps"])
app.include_router(schedule.router, prefix="/schedule", tags=["Schedule"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Smart Campus App API",
        "version": settings.APP_VERSION,
        "university": "Babcock University",
        "status": "operational",
        "documentation": "/docs" if settings.DEBUG else "Documentation disabled in production"
    }

@app.get("/health")
async def health_check():
    """Enhanced health check with comprehensive system status"""
    try:
        start_time = time.time()
        db_healthy = await check_database_health()
        check_duration = time.time() - start_time
        
        health_data = {
            "status": "healthy" if db_healthy else "degraded",
            "message": "Smart Campus App is running",
            "version": settings.APP_VERSION,
            "timestamp": time.time(),
            "checks": {
                "database": {
                    "status": "connected" if db_healthy else "disconnected",
                    "response_time": f"{check_duration:.3f}s"
                },
                "api": {
                    "status": "operational",
                    "response_time": f"{time.time() - start_time:.3f}s"
                }
            }
        }
        
        if not db_healthy:
            health_data["status"] = "degraded"
            health_data["message"] = "Smart Campus App is running but database is unavailable"
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": "Smart Campus App health check failed",
            "version": settings.APP_VERSION,
            "timestamp": time.time(),
            "error": str(e)
        }

@app.get("/db-status")
async def database_status():
    """Check database connection status specifically"""
    try:
        start_time = time.time()
        db_healthy = await check_database_health()
        response_time = time.time() - start_time
        
        if db_healthy:
            return {
                "status": "connected", 
                "message": "Database is accessible",
                "response_time": f"{response_time:.3f}s"
            }
        else:
            return {
                "status": "disconnected", 
                "message": "Database is not accessible",
                "response_time": f"{response_time:.3f}s"
            }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Database check failed: {str(e)}",
            "timestamp": time.time()
        }

@app.get("/info")
async def api_info():
    """Get API information and configuration details"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": "production" if not settings.DEBUG else "development",
        "debug": settings.DEBUG,
        "features": {
            "authentication": True,
            "maps": True,
            "attendance": True,
            "cafeteria": True,
            "schedule": True,
            "chat": True,
            "file_upload": True
        },
        "database": {
            "type": "MongoDB",
            "name": settings.MONGODB_DATABASE
        },
        "security": {
            "cors_enabled": True,
            "trusted_hosts": not settings.DEBUG,
            "compression": True
        }
    }

@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle CORS preflight requests"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": ",".join(settings.ALLOWED_ORIGINS),
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info" if not settings.DEBUG else "debug"
    ) 
