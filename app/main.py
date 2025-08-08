from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager

from .core.config import settings
from .database import connect_to_mongo, close_mongo_connection
from .routers import auth, users, attendance, cafeteria, maps, schedule, chat

# Security
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Smart Campus App API for Babcock University",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    return {"status": "healthy", "message": "Smart Campus App is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 