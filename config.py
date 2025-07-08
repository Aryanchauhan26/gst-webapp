#!/usr/bin/env python3
"""
Enhanced Configuration Manager for GST Intelligence Platform
Production-ready configuration with validation and security
"""

import os
import secrets
import logging
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from pydantic import BaseSettings, Field, validator, root_validator
from pydantic.networks import AnyHttpUrl, PostgresDsn, RedisDsn
from functools import lru_cache

logger = logging.getLogger(__name__)


class SecuritySettings(BaseSettings):
    """Security-related configuration"""

    # Session and JWT settings
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT and session encryption")

    SESSION_SECURE: bool = Field(
        default=True, description="Use secure cookies in production")

    SESSION_HTTPONLY: bool = Field(default=True,
                                   description="HTTP-only session cookies")

    SESSION_SAMESITE: str = Field(default="lax",
                                  description="SameSite cookie attribute")

    SESSION_EXPIRE_MINUTES: int = Field(
        default=1440,  # 24 hours
        description="Session expiration time in minutes")

    # Password and encryption settings
    PASSWORD_MIN_LENGTH: int = Field(default=8, ge=6, le=128)
    PASSWORD_REQUIRE_UPPERCASE: bool = Field(default=True)
    PASSWORD_REQUIRE_LOWERCASE: bool = Field(default=True)
    PASSWORD_REQUIRE_NUMBERS: bool = Field(default=True)
    PASSWORD_REQUIRE_SPECIAL: bool = Field(default=True)

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_REQUESTS_PER_HOUR: int = Field(default=1000)

    # Two-factor authentication
    ENABLE_2FA: bool = Field(default=False)
    TOTP_ISSUER: str = Field(default="GST Intelligence Platform")

    # API security
    API_KEY_HEADER: str = Field(default="X-API-Key")
    REQUIRE_API_KEY: bool = Field(default=False)

    @validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        if v == "your-super-secret-key-change-this-in-production":
            logger.warning(
                "🚨 SECURITY WARNING: Using default SECRET_KEY in production!")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @validator('SESSION_SAMESITE')
    def validate_session_samesite(cls, v):
        if v.lower() not in ['strict', 'lax', 'none']:
            raise ValueError(
                "SESSION_SAMESITE must be 'strict', 'lax', or 'none'")
        return v.lower()


class DatabaseSettings(BaseSettings):
    """Database configuration"""

    # PostgreSQL settings
    POSTGRES_DSN: PostgresDsn = Field(
        default=
        "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
        description="PostgreSQL connection string")

    POSTGRES_POOL_MIN_SIZE: int = Field(default=2, ge=1, le=100)
    POSTGRES_POOL_MAX_SIZE: int = Field(default=20, ge=1, le=100)
    POSTGRES_POOL_MAX_QUERIES: int = Field(default=50000, ge=1000)
    POSTGRES_POOL_MAX_INACTIVE_TIME: int = Field(default=300, ge=60)
    POSTGRES_COMMAND_TIMEOUT: int = Field(default=30, ge=5, le=300)

    # Redis settings (optional)
    REDIS_URL: Optional[str] = Field(
        default=None, description="Redis connection URL (optional)")

    REDIS_POOL_SIZE: int = Field(default=10, ge=1, le=100)
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, ge=1, le=60)
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(default=5, ge=1, le=60)

    # Database maintenance
    AUTO_CLEANUP_ENABLED: bool = Field(default=True)
    CLEANUP_INTERVAL_HOURS: int = Field(default=24, ge=1, le=168)
    KEEP_LOGS_DAYS: int = Field(default=30, ge=7, le=365)
    KEEP_SESSIONS_DAYS: int = Field(default=7, ge=1, le=30)

    @validator('POSTGRES_POOL_MAX_SIZE')
    def validate_pool_max_size(cls, v, values):
        min_size = values.get('POSTGRES_POOL_MIN_SIZE', 2)
        if v < min_size:
            raise ValueError(
                "POSTGRES_POOL_MAX_SIZE must be >= POSTGRES_POOL_MIN_SIZE")
        return v


class APISettings(BaseSettings):
    """External API configuration"""

    # RapidAPI for GST data
    RAPIDAPI_KEY: str = Field(
        default="ea9dafb3d8msh73c253dbf6a335ep111a12jsne515c06eb3ed",
        description="RapidAPI key for GST services")

    RAPIDAPI_HOST: str = Field(default="gst-return-status.p.rapidapi.com",
                               description="RapidAPI host for GST services")

    RAPIDAPI_TIMEOUT: int = Field(default=30, ge=5, le=120)
    RAPIDAPI_MAX_RETRIES: int = Field(default=3, ge=1, le=5)

    # Anthropic AI API
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None, description="Anthropic API key for AI features")

    ANTHROPIC_MODEL: str = Field(default="claude-3-haiku-20240307")
    ANTHROPIC_MAX_TOKENS: int = Field(default=1000, ge=100, le=4000)
    ANTHROPIC_TIMEOUT: int = Field(default=30, ge=5, le=120)

    # Razorpay for payments
    RAZORPAY_KEY_ID: Optional[str] = Field(default=None)
    RAZORPAY_KEY_SECRET: Optional[str] = Field(default=None)
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = Field(default=None)
    RAZORPAY_SANDBOX: bool = Field(default=True)

    # Google services (optional)
    GOOGLE_MAPS_API_KEY: Optional[str] = Field(default=None)
    GOOGLE_ANALYTICS_ID: Optional[str] = Field(default=None)

    @validator('RAPIDAPI_KEY')
    def validate_rapidapi_key(cls, v):
        if v == "your-rapidapi-key":
            logger.warning("⚠️ WARNING: Using default RAPIDAPI_KEY")
        return v


class FeatureSettings(BaseSettings):
    """Feature flags and toggles"""

    # Core features
    ENABLE_AI_FEATURES: bool = Field(default=True)
    ENABLE_LOAN_MANAGEMENT: bool = Field(default=True)
    ENABLE_ADVANCED_ANALYTICS: bool = Field(default=True)
    ENABLE_EXPORT_FEATURES: bool = Field(default=True)
    ENABLE_NOTIFICATIONS: bool = Field(default=True)

    # UI features
    ENABLE_DARK_MODE: bool = Field(default=True)
    ENABLE_PWA: bool = Field(default=True)
    ENABLE_OFFLINE_MODE: bool = Field(default=True)

    # Admin features
    ENABLE_ADMIN_PANEL: bool = Field(default=True)
    ENABLE_USER_MANAGEMENT: bool = Field(default=True)
    ENABLE_SYSTEM_MONITORING: bool = Field(default=True)

    # Experimental features
    ENABLE_BETA_FEATURES: bool = Field(default=False)
    ENABLE_ADVANCED_SEARCH: bool = Field(default=False)
    ENABLE_ML_PREDICTIONS: bool = Field(default=False)


class ApplicationSettings(BaseSettings):
    """Main application configuration"""

    # Environment and basic settings
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    TESTING: bool = Field(default=False)
    VERSION: str = Field(default="2.0.0")

    # Application details
    APP_NAME: str = Field(default="GST Intelligence Platform")
    APP_DESCRIPTION: str = Field(
        default=
        "Advanced GST Compliance Analytics Platform with AI-powered insights")

    # Server settings
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000, ge=1, le=65535)
    WORKERS: int = Field(default=1, ge=1, le=32)

    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins")

    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"])

    # Logging settings
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_FILE: Optional[str] = Field(default=None)
    LOG_MAX_SIZE: int = Field(default=10 * 1024 * 1024)  # 10MB
    LOG_BACKUP_COUNT: int = Field(default=5)

    # File upload settings
    MAX_UPLOAD_SIZE: int = Field(default=10 * 1024 * 1024)  # 10MB
    ALLOWED_UPLOAD_TYPES: List[str] = Field(
        default=["image/jpeg", "image/png", "application/pdf", "text/csv"])

    UPLOAD_DIR: str = Field(default="uploads")

    # Cache settings
    CACHE_DEFAULT_TTL: int = Field(default=3600)  # 1 hour
    CACHE_MAX_ENTRIES: int = Field(default=10000)

    @validator('ENVIRONMENT')
    def validate_environment(cls, v):
        allowed_envs = ['development', 'staging', 'production', 'testing']
        if v.lower() not in allowed_envs:
            raise ValueError(f"ENVIRONMENT must be one of: {allowed_envs}")
        return v.lower()

    @validator('LOG_LEVEL')
    def validate_log_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {allowed_levels}")
        return v.upper()

    @validator('CORS_ORIGINS')
    def validate_cors_origins(cls, v, values):
        environment = values.get('ENVIRONMENT', 'development')
        if environment == 'production' and '*' in v:
            logger.warning(
                "🚨 SECURITY WARNING: Using wildcard CORS origins in production!"
            )
        return v

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == 'production'

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == 'development'

    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.TESTING or self.ENVIRONMENT == 'testing'


class EnhancedSettings(BaseSettings):
    """Complete application settings"""

    # Sub-configurations
    app: ApplicationSettings = Field(default_factory=ApplicationSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: APISettings = Field(default_factory=APISettings)
    features: FeatureSettings = Field(default_factory=FeatureSettings)

    class Config:
        env_file = [".env", ".env.local", ".env.production"]
        env_file_encoding = 'utf-8'
        case_sensitive = True
        env_nested_delimiter = '__'

        # Allow configuration from environment variables
        # Example: APP__DEBUG=true -> app.DEBUG = True
        # Example: DATABASE__POSTGRES_POOL_MAX_SIZE=50 -> database.POSTGRES_POOL_MAX_SIZE = 50

    @root_validator
    def validate_configuration(cls, values):
        """Cross-validation of settings"""
        app_settings = values.get('app')
        security_settings = values.get('security')
        api_settings = values.get('api')
        features = values.get('features')

        if not app_settings or not security_settings:
            return values

        # Production security checks
        if app_settings.is_production():
            if app_settings.DEBUG:
                logger.warning("🚨 DEBUG is enabled in production!")

            if not security_settings.SESSION_SECURE:
                logger.warning(
                    "🚨 SESSION_SECURE should be True in production!")

            if security_settings.SECRET_KEY == "your-super-secret-key-change-this-in-production":
                raise ValueError(
                    "🚨 CRITICAL: Must set SECRET_KEY in production!")

        # Feature dependency checks
        if features and features.ENABLE_AI_FEATURES and not api_settings.ANTHROPIC_API_KEY:
            logger.warning(
                "⚠️ AI features enabled but no Anthropic API key configured")

        if features and features.ENABLE_LOAN_MANAGEMENT:
            if not api_settings.RAZORPAY_KEY_ID or not api_settings.RAZORPAY_KEY_SECRET:
                logger.warning(
                    "⚠️ Loan management enabled but Razorpay credentials not configured"
                )

        return values

    def get_validation_warnings(self) -> List[str]:
        """Get configuration validation warnings"""
        warnings = []

        # Check critical settings
        if self.security.SECRET_KEY == "your-super-secret-key-change-this-in-production":
            warnings.append("🚨 CRITICAL: SECRET_KEY is using default value!")

        if self.database.POSTGRES_DSN == "postgresql://user:pass@localhost:5432/dbname":
            warnings.append("🚨 CRITICAL: POSTGRES_DSN is using default value!")

        if self.api.RAPIDAPI_KEY == "your-rapidapi-key":
            warnings.append(
                "⚠️ WARNING: RAPIDAPI_KEY not configured - GST features disabled"
            )

        # Production-specific checks
        if self.app.is_production():
            if not self.security.SESSION_SECURE:
                warnings.append(
                    "🚨 PRODUCTION: SESSION_SECURE should be True in production"
                )

            if self.app.DEBUG:
                warnings.append(
                    "🚨 PRODUCTION: DEBUG should be False in production")

            if "*" in self.app.CORS_ORIGINS:
                warnings.append(
                    "🚨 PRODUCTION: CORS_ORIGINS should not include '*' in production"
                )

            if not self.database.REDIS_URL:
                warnings.append(
                    "⚠️ PRODUCTION: REDIS_URL not configured - using memory cache"
                )

        # Feature-specific checks
        if self.features.ENABLE_AI_FEATURES and not self.api.ANTHROPIC_API_KEY:
            warnings.append(
                "⚠️ AI features enabled but ANTHROPIC_API_KEY not configured")

        if self.features.ENABLE_LOAN_MANAGEMENT and (
                not self.api.RAZORPAY_KEY_ID
                or not self.api.RAZORPAY_KEY_SECRET):
            warnings.append(
                "⚠️ Loan management enabled but Razorpay credentials not configured"
            )

        return warnings

    def print_startup_info(self):
        """Print startup information and warnings"""
        print("=" * 80)
        print(f"🚀 {self.app.APP_NAME} v{self.app.VERSION}")
        print("=" * 80)
        print(f"📍 Environment: {self.app.ENVIRONMENT.upper()}")
        print(f"🐛 Debug Mode: {'ON' if self.app.DEBUG else 'OFF'}")
        print(f"🌐 Host: {self.app.HOST}:{self.app.PORT}")
        print(
            f"📊 Database: {'PostgreSQL' + (' + Redis' if self.database.REDIS_URL else '')}"
        )
        print(
            f"🔐 Security: {'Production' if self.app.is_production() else 'Development'}"
        )

        # Feature status
        print("\n📋 Feature Status:")
        feature_dict = self.features.dict()
        for feature, enabled in feature_dict.items():
            status = "✅ ON" if enabled else "❌ OFF"
            feature_name = feature.replace('ENABLE_', '').replace('_',
                                                                  ' ').title()
            print(f"   {feature_name}: {status}")

        # Configuration warnings
        warnings = self.get_validation_warnings()
        if warnings:
            print("\n⚠️ Configuration Warnings:")
            for warning in warnings:
                print(f"   {warning}")
        else:
            print("\n✅ Configuration validated successfully!")

        print("=" * 80)

    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration for FastAPI"""
        return {
            "allow_origins": self.app.CORS_ORIGINS,
            "allow_credentials": self.app.CORS_ALLOW_CREDENTIALS,
            "allow_methods": self.app.CORS_ALLOW_METHODS,
            "allow_headers": self.app.CORS_ALLOW_HEADERS,
        }

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": self.app.LOG_FORMAT,
                },
                "detailed": {
                    "format":
                    "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": self.app.LOG_LEVEL,
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": self.app.LOG_LEVEL,
                "handlers": ["console"],
            },
        }

        # Add file handler if LOG_FILE is specified
        if self.app.LOG_FILE:
            config["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": self.app.LOG_LEVEL,
                "formatter": "detailed",
                "filename": self.app.LOG_FILE,
                "maxBytes": self.app.LOG_MAX_SIZE,
                "backupCount": self.app.LOG_BACKUP_COUNT,
            }
            config["root"]["handlers"].append("file")

        return config


@lru_cache()
def get_settings() -> EnhancedSettings:
    """Get cached settings instance"""
    return EnhancedSettings()


# Create global settings instance
settings = get_settings()

# Legacy compatibility - expose commonly used settings at module level
SECRET_KEY = settings.security.SECRET_KEY
POSTGRES_DSN = settings.database.POSTGRES_DSN
RAPIDAPI_KEY = settings.api.RAPIDAPI_KEY
ANTHROPIC_API_KEY = settings.api.ANTHROPIC_API_KEY
ENVIRONMENT = settings.app.ENVIRONMENT
DEBUG = settings.app.DEBUG

# Print startup info when module is imported
if __name__ != "__main__":
    settings.print_startup_info()

# Example of how to use in your application
if __name__ == "__main__":
    # Test configuration
    print("🧪 Testing configuration...")

    # Create settings instance
    test_settings = EnhancedSettings()

    # Print startup info
    test_settings.print_startup_info()

    # Test validation warnings
    warnings = test_settings.get_validation_warnings()
    if warnings:
        print(f"\n⚠️ Found {len(warnings)} configuration warnings")
    else:
        print("\n✅ All configuration checks passed!")

    # Test CORS config
    cors_config = test_settings.get_cors_config()
    print(f"\n🌐 CORS Configuration: {cors_config}")

    # Test logging config
    logging_config = test_settings.get_logging_config()
    print(f"\n📝 Logging Configuration: {logging_config}")

    print("\n✅ Configuration test completed successfully!")
