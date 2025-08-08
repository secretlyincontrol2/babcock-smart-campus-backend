import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # MongoDB Database
    MONGODB_URL: str = "mongodb+srv://bu22-2130:bu22-2130@cluster0.4nsgp2g.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    MONGODB_DATABASE: str = "smart_campus_db"
    
    # Security
    SECRET_KEY: str = "smart-campus-app-secret-key-2024-babcock-university"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Google Maps API
    GOOGLE_MAPS_API_KEY: str = "AIzaSyAa-XKO4DH_CLf647SMZYypDOfk0d1SBUE"
    
    # QR Code Settings
    QR_CODE_SIZE: int = 10
    QR_CODE_BORDER: int = 4
    
    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    
    # Redis (for caching and sessions)
    REDIS_URL: Optional[str] = None
    
    # Email Settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # App Settings
    APP_NAME: str = "Smart Campus App"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # CORS Settings
    ALLOWED_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

# Create settings instance
settings = Settings()

# Update MongoDB URL for Railway
if os.getenv("MONGODB_URL"):
    settings.MONGODB_URL = os.getenv("MONGODB_URL")
if os.getenv("MONGODB_DATABASE"):
    settings.MONGODB_DATABASE = os.getenv("MONGODB_DATABASE") 