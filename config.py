# config.py - Enhanced configuration with validation
import os
from typing import Optional, List
from pydantic import BaseSettings, validator, AnyHttpUrl

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str
    SESSION_DURATION: int = 2592000  # 30 days
    
    # Database
    POSTGRES_DSN: str
    
    # Redis
    REDIS_URL: Optional[str] = None
    
    # APIs
    RAPIDAPI_KEY: str
    RAPIDAPI_HOST: str = "gst-return-status.p.rapidapi.com"
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600
    
    # CORS
    CORS_ORIGINS: List[AnyHttpUrl] = []
    CORS_CREDENTIALS: bool = True
    
    # Features
    ENABLE_AI_FEATURES: bool = True
    ENABLE_PDF_GENERATION: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_ANALYTICS: bool = True
    
    @validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v
    
    @validator('POSTGRES_DSN')
    def validate_postgres_dsn(cls, v):
        if not v.startswith(('postgresql://', 'postgres://')):
            raise ValueError('POSTGRES_DSN must be a valid PostgreSQL connection string')
        return v
    
    @validator('CORS_ORIGINS', pre=True)
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            return [url.strip() for url in v.split(',') if url.strip()]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Initialize configuration
config = Settings()