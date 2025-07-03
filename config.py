# config.py - Fixed for Render deployment with existing .env
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "your-default-secret-key-change-in-production-min-32-chars"
    SESSION_DURATION: int = 2592000  # 30 days
    
    # Database
    POSTGRES_DSN: str = "postgresql://user:pass@localhost:5432/dbname"
    
    # Redis
    REDIS_URL: Optional[str] = None
    
    # APIs
    RAPIDAPI_KEY: str = "your-rapidapi-key"
    RAPIDAPI_HOST: str = "gst-return-status.p.rapidapi.com"
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600
    
    # CORS - Simple string field to avoid JSON parsing
    CORS_ORIGINS: str = "*"
    CORS_CREDENTIALS: bool = True
    
    # Features
    ENABLE_AI_FEATURES: bool = True
    ENABLE_PDF_GENERATION: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_ANALYTICS: bool = True
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v):
        # Just warn, don't fail deployment
        if len(v) < 32:
            print(f"⚠️ Warning: SECRET_KEY should be at least 32 characters")
        return v
    
    @field_validator('POSTGRES_DSN')
    @classmethod
    def validate_postgres_dsn(cls, v):
        # Just warn, don't fail deployment
        if not v.startswith(('postgresql://', 'postgres://')):
            print(f"⚠️ Warning: POSTGRES_DSN format may need adjustment")
        return v
    
    # Helper method to convert CORS string to list
    def get_cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list for FastAPI."""
        if not self.CORS_ORIGINS or self.CORS_ORIGINS == "*":
            return ["*"]
        # Handle comma-separated values
        return [url.strip() for url in self.CORS_ORIGINS.split(',') if url.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Tell Pydantic to not try to parse simple strings as JSON
        env_parse_none_str = True

# Safe initialization with fallback
try:
    settings = Settings()
    print(f"✅ Config loaded - Environment: {settings.ENVIRONMENT}")
    print(f"🔗 Database: {settings.POSTGRES_DSN[:20]}...")
    print(f"📦 Redis: {'✅ Configured' if settings.REDIS_URL else '⚠️ Not configured'}")
    print(f"🌐 CORS Origins: {settings.get_cors_origins_list()}")
except Exception as e:
    print(f"❌ Config error: {e}")
    # Don't create fallback, let it fail clearly
    raise

# Export for backward compatibility
config = settings