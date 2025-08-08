import os
from typing import Optional

class Settings:
    def __init__(self):
        # MongoDB Database
        self.MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb+srv://bu22-2130:bu22-2130@cluster0.4nsgp2g.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
        self.MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "smart_campus_db")

        # Security
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "smart-campus-app-secret-key-2024-babcock-university")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

        # Google Maps API
        self.GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyAa-XKO4DH_CLf647SMZYypDOfk0d1SBUE")

        # QR Code Settings
        self.QR_CODE_SIZE: int = int(os.getenv("QR_CODE_SIZE", "10"))
        self.QR_CODE_BORDER: int = int(os.getenv("QR_CODE_BORDER", "4"))

        # File Upload
        self.UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
        self.MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(5 * 1024 * 1024)))  # 5MB

        # Redis (for caching and sessions)
        self.REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

        # Email Settings
        self.SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
        self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME")
        self.SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")

        # App Settings
        self.APP_NAME: str = os.getenv("APP_NAME", "Smart Campus App")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

        # CORS Settings - Configure for production with specific origins
        cors_origins = os.getenv("ALLOWED_ORIGINS", "https://babcock-smart-campus-frontend.onrender.com")
        if cors_origins == "*":
            self.ALLOWED_ORIGINS = ["*"]
        else:
            self.ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(",")]

# Create settings instance
settings = Settings() 