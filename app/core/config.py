import os
from typing import Optional

class Settings:
    def __init__(self):
        # MongoDB Database - Updated with correct cluster hostname
        default_mongodb_url = "mongodb+srv://bu22-2130:bu22-2130@ac-uyow51n-shard-00-00.4nsgp2g.mongodb.net/smart_campus_db?retryWrites=true&w=majority&appName=Cluster0&tls=true&tlsAllowInvalidCertificates=true"
        self.MONGODB_URL: str = os.getenv("MONGODB_URL", default_mongodb_url)
        self.MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "smart_campus_db")
        
        # Validate and fix MongoDB URL if needed
        self._validate_mongodb_url()
        
        # Security
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "smart-campus-app-secret-key-2024-babcock-university")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        
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
        self.DEMO_MODE: bool = os.getenv("DEMO_MODE", "False").lower() == "true"
        
        # CORS Settings - Allow all origins for development
        cors_origins = os.getenv("ALLOWED_ORIGINS", "*")
        if cors_origins == "*":
            self.ALLOWED_ORIGINS = ["*"]
        else:
            self.ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(",")]
    
    def _validate_mongodb_url(self):
        """Validate and fix MongoDB URL if needed."""
        # Check if URL is valid
        if not (self.MONGODB_URL.startswith("mongodb://") or self.MONGODB_URL.startswith("mongodb+srv://")):
            print(f"ERROR: Invalid MongoDB URL scheme. Current URL: {self.MONGODB_URL[:50]}...")
            # Use fallback URL with correct hostname
            self.MONGODB_URL = "mongodb+srv://bu22-2130:bu22-2130@ac-uyow51n-shard-00-00.4nsgp2g.mongodb.net/smart_campus_db?retryWrites=true&w=majority&appName=Cluster0&tls=true&tlsAllowInvalidCertificates=true"
            print("Using fallback MongoDB URL")
        
        # Fix cluster hostname if using old format
        if "cluster0.4nsgp2g.mongodb.net" in self.MONGODB_URL:
            self.MONGODB_URL = self.MONGODB_URL.replace(
                "cluster0.4nsgp2g.mongodb.net", 
                "ac-uyow51n-shard-00-00.4nsgp2g.mongodb.net"
            )
            print("Updated cluster hostname to correct format")
        
        # Check if URL includes database name
        if "mongodb+srv://" in self.MONGODB_URL and "/" not in self.MONGODB_URL.split("@")[1].split("?")[0]:
            # Add database name to URL
            parts = self.MONGODB_URL.split("?")
            base_url = parts[0]
            query_params = "?" + parts[1] if len(parts) > 1 else ""
            
            if not base_url.endswith("/"):
                base_url += "/"
            base_url += self.MONGODB_DATABASE
            
            self.MONGODB_URL = base_url + query_params
            print(f"Added database name to MongoDB URL")
        
        # Ensure proper TLS parameters for modern MongoDB
        if "tls=true" not in self.MONGODB_URL and "ssl=true" not in self.MONGODB_URL:
            separator = "&" if "?" in self.MONGODB_URL else "?"
            self.MONGODB_URL += f"{separator}tls=true&tlsAllowInvalidCertificates=true"
            print("Added TLS parameters to MongoDB URL")
        elif "ssl=true" in self.MONGODB_URL and "tls=true" not in self.MONGODB_URL:
            # Replace old ssl with new tls
            self.MONGODB_URL = self.MONGODB_URL.replace("ssl=true", "tls=true")
            if "tlsAllowInvalidCertificates=true" not in self.MONGODB_URL:
                self.MONGODB_URL += "&tlsAllowInvalidCertificates=true"
            print("Updated SSL to TLS parameters")
        
        # Debug output (mask password for security)
        masked_url = self.MONGODB_URL.replace("bu22-2130:bu22-2130@", "***:***@")
        print(f"Final MongoDB URL: {masked_url}")

# Create settings instance
settings = Settings()
