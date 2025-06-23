#!/usr/bin/env python3
"""
Configuration management for GST Intelligence Platform
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    POSTGRES_DSN: str = os.getenv(
        "POSTGRES_DSN", 
        "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    )
    
    # API Keys
    RAPIDAPI_KEY: Optional[str] = os.getenv("RAPIDAPI_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    RAPIDAPI_HOST: str = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # App Settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    SESSION_DURATION_DAYS: int = int(os.getenv("SESSION_DURATION_DAYS", "7"))
    MAX_SEARCH_HISTORY: int = int(os.getenv("MAX_SEARCH_HISTORY", "1000"))
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

settings = Settings()