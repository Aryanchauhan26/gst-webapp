import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator


class Settings(BaseSettings):
    # Pydantic v2 configuration
    model_config = ConfigDict(extra='ignore',
                              env_file='.env',
                              case_sensitive=True)

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
    SESSION_DURATION: int = 2592000  # 30 days in seconds
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

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            print(
                f"⚠️ Warning: SECRET_KEY should be at least 32 characters (current: {len(v)})"
            )
        return v

    def get_cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list for FastAPI."""
        if not self.CORS_ORIGINS or self.CORS_ORIGINS == "*":
            return ["*"]
        return [
            url.strip() for url in self.CORS_ORIGINS.split(',') if url.strip()
        ]

    def get_admin_users_list(self) -> List[str]:
        """Convert ADMIN_USERS string to list."""
        if not self.ADMIN_USERS:
            return []
        return [
            user.strip() for user in self.ADMIN_USERS.split(',')
            if user.strip()
        ]

    def is_admin_user(self, user: str) -> bool:
        """Check if user is admin."""
        return user in self.get_admin_users_list()


# Safe initialization
try:
    settings = Settings()
    print("=" * 50)
    print("✅ GST Intelligence Platform - Config Loaded!")
    print("=" * 50)
    print(f"🌍 Environment: {settings.ENVIRONMENT}")
    print(f"🔍 Debug Mode: {settings.DEBUG}")
    print(
        f"🔑 Database: {'✅ Configured' if settings.POSTGRES_DSN else '❌ Missing'}"
    )
    print("=" * 50)
except Exception as e:
    print(f"❌ CONFIG ERROR: {e}")
    raise

# Export for backward compatibility
config = settings
