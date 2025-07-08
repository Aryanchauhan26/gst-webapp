# config.py - Complete working version for production deployment
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator


class Settings(BaseSettings):
    # Pydantic v2 configuration - ignores extra .env variables
    model_config = ConfigDict(
        extra='ignore',  # This is the KEY fix - ignores extra variables
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
            print(
                f"⚠️ Warning: SECRET_KEY should be at least 32 characters (current: {len(v)})"
            )
        return v

    @field_validator('POSTGRES_DSN')
    @classmethod
    def validate_postgres_dsn(cls, v):
        if not v or v == "postgresql://user:pass@localhost:5432/dbname":
            print(
                "⚠️ Warning: Using default database URL. Set POSTGRES_DSN in production."
            )
        return v

    @field_validator('RAPIDAPI_KEY')
    @classmethod
    def validate_rapidapi_key(cls, v):
        if not v or v == "your-rapidapi-key":
            print(
                "⚠️ Warning: RAPIDAPI_KEY not configured. GST API features will not work."
            )
        return v

    # Helper methods
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

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT.lower() == "development"

    def get_database_config(self) -> dict:
        """Get database configuration for asyncpg."""
        return {
            'dsn': self.POSTGRES_DSN,
            'min_size': 5,
            'max_size': 20 if self.is_production() else 10,
            'command_timeout': 60,
            'server_settings': {
                'jit': 'off',
                'application_name': 'gst_intelligence'
            }
        }

    def get_redis_config(self) -> Optional[dict]:
        """Get Redis configuration."""
        if not self.REDIS_URL:
            return None

        return {
            'url': self.REDIS_URL,
            'decode_responses': True,
            'retry_on_timeout': True,
            'socket_timeout': 5,
            'socket_connect_timeout': 5
        }

    def get_logging_config(self) -> dict:
        """Get logging configuration."""
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'default': {
                    'format':
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                },
                'detailed': {
                    'format':
                    '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
                },
            },
            'handlers': {
                'default': {
                    'formatter': 'default',
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stdout',
                },
                'file': {
                    'formatter': 'detailed',
                    'class': 'logging.FileHandler',
                    'filename': 'app.log',
                    'mode': 'a',
                },
            },
            'root': {
                'level':
                self.LOG_LEVEL,
                'handlers':
                ['default'] if self.is_development() else ['default', 'file'],
            },
        }

    def validate_configuration(self) -> List[str]:
        """Validate configuration and return list of warnings/errors."""
        warnings = []

        # Check critical settings
        if self.SECRET_KEY == "your-super-secret-key-change-this-in-production":
            warnings.append("🚨 CRITICAL: SECRET_KEY is using default value!")

        if self.POSTGRES_DSN == "postgresql://user:pass@localhost:5432/dbname":
            warnings.append("🚨 CRITICAL: POSTGRES_DSN is using default value!")

        if self.RAPIDAPI_KEY == "your-rapidapi-key":
            warnings.append(
                "⚠️ WARNING: RAPIDAPI_KEY not configured - GST features disabled"
            )

        # Production-specific checks
        if self.is_production():
            if not self.SESSION_SECURE:
                warnings.append(
                    "🚨 PRODUCTION: SESSION_SECURE should be True in production"
                )

            if self.DEBUG:
                warnings.append(
                    "🚨 PRODUCTION: DEBUG should be False in production")

            if self.CORS_ORIGINS == "*":
                warnings.append(
                    "🚨 PRODUCTION: CORS_ORIGINS should not be '*' in production"
                )

            if not self.REDIS_URL:
                warnings.append(
                    "⚠️ PRODUCTION: REDIS_URL not configured - using memory cache"
                )

        # Feature-specific checks
        if self.ENABLE_AI_FEATURES and not self.ANTHROPIC_API_KEY:
            warnings.append(
                "⚠️ AI features enabled but ANTHROPIC_API_KEY not configured")

        if self.ENABLE_LOAN_MANAGEMENT and (not self.RAZORPAY_KEY_ID
                                            or not self.RAZORPAY_KEY_SECRET):
            warnings.append(
                "⚠️ Loan management enabled but Razorpay credentials not configured"
            )

        return warnings

    def print_startup_info(self):
        """Print startup information."""
        print("\n" + "=" * 60)
        print("🚀 GST Intelligence Platform Starting Up")
        print("=" * 60)
        print(f"Environment: {self.ENVIRONMENT}")
        print(f"Version: {self.VERSION}")
        print(f"Debug Mode: {self.DEBUG}")
        print(f"Host: {self.HOST}:{self.PORT}")
        print("-" * 60)

        # Feature status
        features = [
            ("Database", "✅" if self.POSTGRES_DSN
             != "postgresql://user:pass@localhost:5432/dbname" else "❌"),
            ("Redis Cache", "✅" if self.REDIS_URL else "🔄 Memory"),
            ("GST API",
             "✅" if self.RAPIDAPI_KEY != "your-rapidapi-key" else "❌"),
            ("AI Features", "✅" if self.ANTHROPIC_API_KEY else "❌"),
            ("Loan Management", "✅"
             if self.RAZORPAY_KEY_ID and self.RAZORPAY_KEY_SECRET else "❌"),
            ("PDF Generation", "✅" if self.ENABLE_PDF_GENERATION else "❌"),
        ]

        print("Features:")
        for feature, status in features:
            print(f"  {feature}: {status}")

        # Validation warnings
        warnings = self.validate_configuration()
        if warnings:
            print("-" * 60)
            print("Configuration Warnings:")
            for warning in warnings:
                print(f"  {warning}")

        print("=" * 60 + "\n")


# Create settings instance
settings = Settings()

# Print startup info when module is imported
if __name__ != "__main__":
    settings.print_startup_info()

# For backwards compatibility
config = settings
