# config.py - Compatible with your complete .env file
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator

class Settings(BaseSettings):
    # CRITICAL: This tells Pydantic to ignore extra fields in .env
    model_config = ConfigDict(extra='ignore')
    
    # Core Application Settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    VERSION: str = "2.0.0"
    
    # Database Configuration
    POSTGRES_DSN: str = "postgresql://user:pass@localhost:5432/dbname"
    
    # Redis Configuration
    REDIS_URL: Optional[str] = None
    
    # API Configuration
    RAPIDAPI_KEY: str = "your-rapidapi-key"
    RAPIDAPI_HOST: str = "gst-return-status.p.rapidapi.com"
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Admin Configuration
    ADMIN_USERS: str = ""
    
    # Security Settings
    SESSION_DURATION: int = 2592000  # 30 days
    SESSION_SECURE: bool = False
    CORS_ORIGINS: str = "*"
    CORS_CREDENTIALS: bool = True
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    LOGIN_RATE_LIMIT: int = 5
    LOGIN_RATE_WINDOW: int = 900
    
    # Feature Flags
    ENABLE_AI_FEATURES: bool = True
    ENABLE_LOAN_MANAGEMENT: bool = False
    ENABLE_PDF_GENERATION: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_ANALYTICS: bool = True
    
    # Razorpay (Loan Management)
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_ENVIRONMENT: str = "sandbox"
    
    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@gst-intelligence.com"
    
    # File Storage
    UPLOAD_FOLDER: str = "uploads"
    MAX_CONTENT_LENGTH: int = 16777216  # 16MB
    STATIC_FOLDER: str = "static"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            print(f"⚠️ Warning: SECRET_KEY should be at least 32 characters (current: {len(v)})")
        return v
    
    @field_validator('ADMIN_USERS')
    @classmethod
    def validate_admin_users(cls, v):
        return v
    
    # Helper methods
    def get_cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list for FastAPI."""
        if not self.CORS_ORIGINS or self.CORS_ORIGINS == "*":
            return ["*"]
        return [url.strip() for url in self.CORS_ORIGINS.split(',') if url.strip()]
    
    def get_admin_users_list(self) -> List[str]:
        """Convert ADMIN_USERS string to list."""
        if not self.ADMIN_USERS:
            return []
        return [user.strip() for user in self.ADMIN_USERS.split(',') if user.strip()]
    
    def is_admin_user(self, user: str) -> bool:
        """Check if user is admin."""
        return user in self.get_admin_users_list()
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Safe initialization
try:
    settings = Settings()
    print(f"✅ Config loaded successfully!")
    print(f"🌍 Environment: {settings.ENVIRONMENT}")
    print(f"🔑 Database: {'✅ Neon DB' if 'neon.tech' in settings.POSTGRES_DSN else '✅ Configured'}")
    print(f"📦 Redis: {'✅ Configured' if settings.REDIS_URL else '⚠️ Not configured'}")
    print(f"🔗 RapidAPI: {'✅ Configured' if settings.RAPIDAPI_KEY != 'your-rapidapi-key' else '⚠️ Default key'}")
    print(f"🤖 Anthropic AI: {'✅ Configured' if settings.ANTHROPIC_API_KEY else '⚠️ Not configured'}")
    print(f"👑 Admin Users: {len(settings.get_admin_users_list())} configured")
    print(f"🌐 CORS Origins: {settings.get_cors_origins_list()}")
except Exception as e:
    print(f"❌ Config error: {e}")
    raise

# Export for backward compatibility
config = settings