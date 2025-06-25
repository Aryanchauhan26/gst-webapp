#!/usr/bin/env python3
"""
Configuration management for GST Intelligence Platform
Centralized configuration with environment variable support
"""

import os
from typing import Optional
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Centralized application settings"""
    
    # =============================================================================
    # DATABASE CONFIGURATION
    # =============================================================================
    POSTGRES_DSN: str = os.getenv(
        "POSTGRES_DSN", 
        "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    )
    
    # Database connection pool settings
    DB_POOL_MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
    DB_POOL_MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "10"))
    
    # =============================================================================
    # API KEYS & EXTERNAL SERVICES
    # =============================================================================
    RAPIDAPI_KEY: Optional[str] = os.getenv("RAPIDAPI_KEY")
    RAPIDAPI_HOST: str = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # =============================================================================
    # SECURITY CONFIGURATION
    # =============================================================================
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ADMIN_USERS: str = os.getenv("ADMIN_USERS", "")
    
    # Session configuration
    SESSION_DURATION_DAYS: int = int(os.getenv("SESSION_DURATION_DAYS", "7"))
    SESSION_DURATION = timedelta(days=SESSION_DURATION_DAYS)
    
    # =============================================================================
    # APPLICATION SETTINGS
    # =============================================================================
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Search and history limits
    MAX_SEARCH_HISTORY: int = int(os.getenv("MAX_SEARCH_HISTORY", "1000"))
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # =============================================================================
    # LOAN MANAGEMENT CONFIGURATION
    # =============================================================================
    RAZORPAY_KEY_ID: Optional[str] = os.getenv("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET: Optional[str] = os.getenv("RAZORPAY_KEY_SECRET") 
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    RAZORPAY_ENVIRONMENT: str = os.getenv("RAZORPAY_ENVIRONMENT", "test")
    
    # Loan configuration limits
    MIN_LOAN_AMOUNT: int = int(os.getenv("MIN_LOAN_AMOUNT", "50000"))
    MAX_LOAN_AMOUNT: int = int(os.getenv("MAX_LOAN_AMOUNT", "5000000"))
    MIN_COMPLIANCE_SCORE: int = int(os.getenv("MIN_COMPLIANCE_SCORE", "60"))
    MIN_BUSINESS_VINTAGE_MONTHS: int = int(os.getenv("MIN_BUSINESS_VINTAGE_MONTHS", "6"))
    MIN_ANNUAL_TURNOVER: int = int(os.getenv("MIN_ANNUAL_TURNOVER", "1000000"))
    MAX_LOAN_TO_TURNOVER_RATIO: float = float(os.getenv("MAX_LOAN_TO_TURNOVER_RATIO", "0.5"))
    
    # =============================================================================
    # CACHE CONFIGURATION
    # =============================================================================
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes default
    
    # =============================================================================
    # LOGGING CONFIGURATION
    # =============================================================================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # =============================================================================
    # FEATURE FLAGS
    # =============================================================================
    ENABLE_AI_FEATURES: bool = bool(ANTHROPIC_API_KEY)
    ENABLE_LOAN_MANAGEMENT: bool = bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)
    ENABLE_CACHING: bool = bool(REDIS_URL)
    ENABLE_PDF_GENERATION: bool = os.getenv("ENABLE_PDF_GENERATION", "true").lower() == "true"
    
    # =============================================================================
    # VALIDATION METHODS
    # =============================================================================
    
    def validate_configuration(self) -> tuple[bool, list[str]]:
        """Validate configuration and return any errors"""
        errors = []
        
        # Critical configuration checks
        if not self.POSTGRES_DSN:
            errors.append("POSTGRES_DSN is required")
        
        if not self.SECRET_KEY or self.SECRET_KEY == "your-secret-key-here-change-in-production":
            errors.append("SECRET_KEY must be set to a secure value in production")
        
        # API configuration warnings
        if not self.RAPIDAPI_KEY:
            errors.append("RAPIDAPI_KEY not set - GST search will not work")
        
        # Loan management validation
        if self.ENABLE_LOAN_MANAGEMENT:
            if not self.RAZORPAY_KEY_ID:
                errors.append("RAZORPAY_KEY_ID required for loan management")
            if not self.RAZORPAY_KEY_SECRET:
                errors.append("RAZORPAY_KEY_SECRET required for loan management")
        
        # Production environment checks
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                errors.append("DEBUG should be False in production")
            if not self.REDIS_URL:
                errors.append("REDIS_URL recommended for production caching")
        
        return len(errors) == 0, errors
    
    def get_loan_config(self) -> dict:
        """Get loan configuration as dictionary"""
        return {
            "min_loan_amount": self.MIN_LOAN_AMOUNT,
            "max_loan_amount": self.MAX_LOAN_AMOUNT,
            "min_compliance_score": self.MIN_COMPLIANCE_SCORE,
            "min_business_vintage_months": self.MIN_BUSINESS_VINTAGE_MONTHS,
            "min_annual_turnover": self.MIN_ANNUAL_TURNOVER,
            "max_loan_to_turnover_ratio": self.MAX_LOAN_TO_TURNOVER_RATIO,
            "environment": self.RAZORPAY_ENVIRONMENT
        }
    
    def get_api_config(self) -> dict:
        """Get API configuration as dictionary"""
        return {
            "rapidapi_key": self.RAPIDAPI_KEY,
            "rapidapi_host": self.RAPIDAPI_HOST,
            "anthropic_key": self.ANTHROPIC_API_KEY,
            "has_gst_api": bool(self.RAPIDAPI_KEY),
            "has_ai_features": self.ENABLE_AI_FEATURES
        }
    
    def get_security_config(self) -> dict:
        """Get security configuration as dictionary"""
        return {
            "session_duration": self.SESSION_DURATION,
            "rate_limit_requests": self.RATE_LIMIT_REQUESTS,
            "rate_limit_window": self.RATE_LIMIT_WINDOW,
            "admin_users": [user.strip() for user in self.ADMIN_USERS.split(",") if user.strip()],
            "debug_mode": self.DEBUG
        }
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT.lower() == "development"
    
    def __repr__(self) -> str:
        """String representation of settings (without sensitive data)"""
        return f"""Settings(
    environment={self.ENVIRONMENT},
    debug={self.DEBUG},
    has_database={bool(self.POSTGRES_DSN)},
    has_gst_api={bool(self.RAPIDAPI_KEY)},
    has_ai_features={self.ENABLE_AI_FEATURES},
    has_loan_management={self.ENABLE_LOAN_MANAGEMENT},
    has_caching={self.ENABLE_CACHING}
)"""

# Create singleton settings instance
settings = Settings()

# Validate configuration on import
if __name__ == "__main__":
    # Configuration validation script
    is_valid, errors = settings.validate_configuration()
    
    print("=== GST Intelligence Platform Configuration ===")
    print(settings)
    print()
    
    if is_valid:
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
    
    print("\n=== Feature Status ===")
    print(f"GST API: {'✅ Enabled' if settings.RAPIDAPI_KEY else '❌ Disabled'}")
    print(f"AI Features: {'✅ Enabled' if settings.ENABLE_AI_FEATURES else '❌ Disabled'}")
    print(f"Loan Management: {'✅ Enabled' if settings.ENABLE_LOAN_MANAGEMENT else '❌ Disabled'}")
    print(f"Caching: {'✅ Redis' if settings.REDIS_URL else '⚠️ Memory only'}")
    print(f"PDF Generation: {'✅ Enabled' if settings.ENABLE_PDF_GENERATION else '❌ Disabled'}")
    
    print(f"\n=== Environment: {settings.ENVIRONMENT.upper()} ===")
    if settings.is_production:
        print("🚀 Production mode - ensure all secrets are properly configured")
    else:
        print("🔧 Development mode - some features may use fallbacks")