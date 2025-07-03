# config.py - Enhanced configuration with Pydantic v2 support
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import field_validator, AnyHttpUrl

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "your-default-secret-key-change-in-production"
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
    
    # CORS
    CORS_ORIGINS: List[str] = []
    CORS_CREDENTIALS: bool = True
    
    # Features
    ENABLE_AI_FEATURES: bool = True
    ENABLE_PDF_GENERATION: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_ANALYTICS: bool = True
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v
    
    @field_validator('POSTGRES_DSN')
    @classmethod
    def validate_postgres_dsn(cls, v):
        if not v.startswith(('postgresql://', 'postgres://')):
            raise ValueError('POSTGRES_DSN must be a valid PostgreSQL connection string')
        return v
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            return [url.strip() for url in v.split(',') if url.strip()]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Initialize configuration
settings = Settings()

# For backward compatibility, also export as 'config'
config = settings