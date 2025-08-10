from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
import logging

from .core.config import settings
from .database import connect_to_mongo, close_mongo_connection, check_database_health
from .routers import auth, users, attendance, cafeteria, maps, schedule, chat

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await connect_to_mongo()
        logger.info("✅ Application startup completed successfully")
    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        # Don't raise here, let the app start but mark database as unavailable
    yield
    # Shutdown
    await close_mongo_connection()
    logger.info("Application shutdown completed")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Smart Campus App API for Babcock University",
    lifespan=lifespan
)

# CORS middleware - Configure for production with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://babcock-smart-campus-frontend.onrender.com",
        "https://babcock-smart-campus-app.onrender.com", 
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
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
    return {
        "message": "Welcome to Smart Campus App API",
        "version": settings.APP_VERSION,
        "university": "Babcock University"
    }

@app.get("/health")
async def health_check():
    """Enhanced health check with database status"""
    try:
        db_healthy = await check_database_health()
        if db_healthy:
            return {
                "status": "healthy", 
                "message": "Smart Campus App is running",
                "database": "connected",
                "timestamp": "2025-08-10T11:24:06Z"
            }
        else:
            return {
                "status": "degraded",
                "message": "Smart Campus App is running but database is unavailable",
                "database": "disconnected",
                "timestamp": "2025-08-10T11:24:06Z"
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": "Smart Campus App health check failed",
            "database": "unknown",
            "error": str(e),
            "timestamp": "2025-08-10T11:24:06Z"
        }

@app.get("/db-status")
async def database_status():
    """Check database connection status specifically"""
    try:
        db_healthy = await check_database_health()
        if db_healthy:
            return {"status": "connected", "message": "Database is accessible"}
        else:
            return {"status": "disconnected", "message": "Database is not accessible"}
    except Exception as e:
        return {"status": "error", "message": f"Database check failed: {str(e)}"}

@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle CORS preflight requests"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "https://babcock-smart-campus-frontend.onrender.com",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 