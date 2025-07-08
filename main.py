#!/usr/bin/env python3
"""
GST Intelligence Platform - Complete Main Application
Enhanced with clean architecture and comprehensive functionality
"""

import os
import re
import asyncio
import asyncpg
import hashlib
import secrets
import logging
import json
import httpx
from datetime import datetime, timedelta
from functools import wraps
from razorpay_lending import RazorpayLendingClient, LoanManager, LoanConfig, LoanStatus
from decimal import Decimal, InvalidOperation
from collections import defaultdict
from typing import Optional, Dict, List, Any, Tuple, Union, Callable
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from io import BytesIO, StringIO
from enum import Enum
import jwt
import redis
import fnmatch
import csv
import time
import html
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except ImportError:
    logger.warning("WeasyPrint not available - PDF generation disabled")
    HAS_WEASYPRINT = False
    HTML = None

from dotenv import load_dotenv
from anthro_ai import get_anthropic_synopsis
from pydantic import BaseModel, field_validator, validator

# Load environment variables
load_dotenv()

# Configuration
try:
    from config import settings as config
    print(f"✅ Config loaded successfully - Environment: {config.ENVIRONMENT}")
except Exception as e:
    print(f"❌ Config loading failed: {e}")
    raise


class DataValidator:
    """Enhanced data validator with comprehensive error handling."""

    @staticmethod
    def validate_gstin(gstin: str) -> bool:
        """Validate GSTIN format."""
        if not gstin or len(gstin) != 15:
            return False

        pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'
        return bool(re.match(pattern, gstin.upper()))

    @staticmethod
    def validate_mobile(mobile: str) -> bool:
        """Validate Indian mobile number."""
        if not mobile or len(mobile) != 10:
            return False

        pattern = r'^[6-9][0-9]{9}$'
        return bool(re.match(pattern, mobile))

    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """Sanitize user input."""
        if not input_str:
            return ""

        # Remove HTML tags and escape special characters
        sanitized = html.escape(str(input_str).strip())
        return sanitized


class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"


# Pydantic models
class LoanApplicationRequest(BaseModel):
    gstin: str
    company_name: str
    loan_amount: float
    purpose: str
    tenure_months: int
    annual_turnover: float
    monthly_revenue: float
    compliance_score: float
    business_vintage_months: int

    @field_validator('gstin')
    @classmethod
    def validate_gstin(cls, v):
        if not DataValidator.validate_gstin(v):
            raise ValueError('Invalid GSTIN format')
        return v.upper()

    @field_validator('loan_amount')
    @classmethod
    def validate_loan_amount(cls, v):
        if v <= 0:
            raise ValueError('Loan amount must be positive')
        return v


# Database Manager
class EnhancedDatabaseManager:

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None

    async def initialize(self):
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(dsn=self.dsn,
                                                  min_size=5,
                                                  max_size=20,
                                                  command_timeout=60,
                                                  server_settings={
                                                      'jit':
                                                      'off',
                                                      'application_name':
                                                      'gst_intelligence'
                                                  })

            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")

            logger.info("✅ Database pool initialized successfully")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def execute_query(self, query: str, *args):
        """Execute a query safely with connection management."""
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *args)
        except Exception as e:
            logger.error(f"Database query error: {e}")
            raise

    async def execute_single(self, query: str, *args):
        """Execute a single query and return one result."""
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(query, *args)
        except Exception as e:
            logger.error(f"Database query error: {e}")
            raise

    async def create_tables(self):
        """Create database tables if they don't exist."""
        try:
            async with self.pool.acquire() as conn:
                # Users table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        mobile VARCHAR(10) PRIMARY KEY,
                        password_hash VARCHAR(255) NOT NULL,
                        salt VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        role VARCHAR(10) DEFAULT 'user'
                    )
                """)

                # Sessions table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        token VARCHAR(255) PRIMARY KEY,
                        user_mobile VARCHAR(10) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        FOREIGN KEY (user_mobile) REFERENCES users(mobile) ON DELETE CASCADE
                    )
                """)

                # Search history table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS search_history (
                        id SERIAL PRIMARY KEY,
                        user_mobile VARCHAR(10) NOT NULL,
                        gstin VARCHAR(15) NOT NULL,
                        company_name TEXT,
                        compliance_score DECIMAL(5,2),
                        search_data JSONB,
                        searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_mobile) REFERENCES users(mobile) ON DELETE CASCADE
                    )
                """)

                # Error logs table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS error_logs (
                        id SERIAL PRIMARY KEY,
                        user_mobile VARCHAR(10),
                        error_type VARCHAR(50),
                        message TEXT,
                        stack_trace TEXT,
                        request_data JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create indexes for performance
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_user_mobile 
                    ON user_sessions(user_mobile)
                """)

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_search_history_user_mobile 
                    ON search_history(user_mobile, searched_at DESC)
                """)

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_search_history_gstin 
                    ON search_history(gstin)
                """)

                logger.info("✅ Database tables created/verified successfully")

        except Exception as e:
            logger.error(f"❌ Table creation failed: {e}")
            raise

    async def create_user(self, mobile: str, password: str) -> bool:
        """Create a new user."""
        try:
            if not DataValidator.validate_mobile(mobile):
                return False

            salt = secrets.token_hex(16)
            password_hash = hashlib.sha256(
                (password + salt).encode()).hexdigest()

            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO users (mobile, password_hash, salt)
                    VALUES ($1, $2, $3)
                """, mobile, password_hash, salt)

            return True

        except asyncpg.UniqueViolationError:
            return False
        except Exception as e:
            logger.error(f"User creation error: {e}")
            return False

    async def verify_user(self, mobile: str, password: str) -> bool:
        """Verify user credentials."""
        try:
            async with self.pool.acquire() as conn:
                user = await conn.fetchrow(
                    """
                    SELECT password_hash, salt FROM users 
                    WHERE mobile = $1 AND is_active = TRUE
                """, mobile)

            if not user:
                return False

            expected_hash = hashlib.sha256(
                (password + user['salt']).encode()).hexdigest()
            return user['password_hash'] == expected_hash

        except Exception as e:
            logger.error(f"User verification error: {e}")
            return False

    async def create_session(self, mobile: str) -> str:
        """Create a new session."""
        try:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(
                seconds=config.SESSION_DURATION)

            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO user_sessions (token, user_mobile, expires_at)
                    VALUES ($1, $2, $3)
                """, token, mobile, expires_at)

            return token

        except Exception as e:
            logger.error(f"Session creation error: {e}")
            return None

    async def get_user_from_session(self, token: str) -> Optional[str]:
        """Get user from session token."""
        try:
            async with self.pool.acquire() as conn:
                session = await conn.fetchrow(
                    """
                    SELECT user_mobile FROM user_sessions 
                    WHERE token = $1 AND expires_at > CURRENT_TIMESTAMP AND is_active = TRUE
                """, token)

            return session['user_mobile'] if session else None

        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None

    async def save_search(self, user_mobile: str, gstin: str,
                          company_name: str, compliance_score: float,
                          search_data: dict):
        """Save search to history."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO search_history (user_mobile, gstin, company_name, compliance_score, search_data)
                    VALUES ($1, $2, $3, $4, $5)
                """, user_mobile, gstin, company_name, compliance_score,
                    json.dumps(search_data))

        except Exception as e:
            logger.error(f"Save search error: {e}")

    async def get_search_history(self,
                                 user_mobile: str,
                                 limit: int = 10) -> List[Dict]:
        """Get user's search history."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT gstin, company_name, compliance_score, searched_at 
                    FROM search_history 
                    WHERE user_mobile = $1 
                    ORDER BY searched_at DESC 
                    LIMIT $2
                """, user_mobile, limit)

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Get search history error: {e}")
            return []

    async def get_all_searches(self, user_mobile: str) -> List[Dict]:
        """Get all user searches."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM search_history 
                    WHERE user_mobile = $1 
                    ORDER BY searched_at DESC
                """, user_mobile)

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Get all searches error: {e}")
            return []

    async def get_user_profile(self, mobile: str) -> Dict:
        """Get user profile information."""
        try:
            async with self.pool.acquire() as conn:
                user = await conn.fetchrow(
                    """
                    SELECT mobile, created_at, last_login, role
                    FROM users WHERE mobile = $1
                """, mobile)

            if not user:
                return {}

                # Get search statistics
                search_stats = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total_searches,
                        COUNT(DISTINCT gstin) as unique_companies,
                        AVG(compliance_score) as avg_compliance
                    FROM search_history 
                    WHERE user_mobile = $1
                """, mobile)

            return {
                **dict(user), 'total_searches':
                search_stats['total_searches'] or 0,
                'unique_companies':
                search_stats['unique_companies'] or 0,
                'avg_compliance':
                float(search_stats['avg_compliance'])
                if search_stats['avg_compliance'] else 0
            }

        except Exception as e:
            logger.error(f"Get user profile error: {e}")
            return {}

    async def update_last_login(self, mobile: str):
        """Update user's last login time."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE users SET last_login = CURRENT_TIMESTAMP 
                    WHERE mobile = $1
                """, mobile)

        except Exception as e:
            logger.error(f"Update last login error: {e}")

    async def get_user_stats(self, user_mobile: str) -> Dict:
        """Get user statistics."""
        try:
            async with self.pool.acquire() as conn:
                stats = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total_searches,
                        COUNT(DISTINCT gstin) as unique_companies,
                        AVG(compliance_score) as avg_compliance,
                        COUNT(CASE WHEN searched_at >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as recent_searches,
                        MAX(searched_at) as last_search
                    FROM search_history 
                    WHERE user_mobile = $1
                """, user_mobile)

            return dict(stats) if stats else {
                'total_searches': 0,
                'unique_companies': 0,
                'avg_compliance': 0,
                'recent_searches': 0,
                'last_search': None
            }

        except Exception as e:
            logger.error(f"Get user stats error: {e}")
            return {
                'total_searches': 0,
                'unique_companies': 0,
                'avg_compliance': 0,
                'recent_searches': 0,
                'last_search': None
            }

    async def get_analytics_data(self, user_mobile: str) -> Dict:
        """Get analytics data for user."""
        try:
            async with self.pool.acquire() as conn:
                # Daily search activity (last 30 days)
                daily_searches = await conn.fetch(
                    """
                    SELECT DATE(searched_at) as date, COUNT(*) as count
                    FROM search_history 
                    WHERE user_mobile = $1 AND searched_at >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY DATE(searched_at)
                    ORDER BY date
                """, user_mobile)

                # Score distribution
                score_distribution = await conn.fetch(
                    """
                    SELECT 
                        CASE 
                            WHEN compliance_score >= 80 THEN 'Excellent'
                            WHEN compliance_score >= 60 THEN 'Good'
                            WHEN compliance_score >= 40 THEN 'Average'
                            ELSE 'Poor'
                        END as category,
                        COUNT(*) as count
                    FROM search_history 
                    WHERE user_mobile = $1 AND compliance_score IS NOT NULL
                    GROUP BY category
                """, user_mobile)

                # Top companies
                top_companies = await conn.fetch(
                    """
                    SELECT company_name, compliance_score, searched_at
                    FROM search_history 
                    WHERE user_mobile = $1 AND company_name IS NOT NULL
                    ORDER BY searched_at DESC
                    LIMIT 10
                """, user_mobile)

            return {
                'daily_searches': [dict(row) for row in daily_searches],
                'score_distribution':
                [dict(row) for row in score_distribution],
                'top_companies': [dict(row) for row in top_companies]
            }

        except Exception as e:
            logger.error(f"Get analytics error: {e}")
            return {
                'daily_searches': [],
                'score_distribution': [],
                'top_companies': []
            }

    async def get_admin_stats(self) -> Dict:
        """Get admin dashboard statistics."""
        try:
            async with self.pool.acquire() as conn:
                # Total users
                total_users = await conn.fetchval("SELECT COUNT(*) FROM users")

                # Active users (logged in last 30 days)
                active_users = await conn.fetchval("""
                    SELECT COUNT(*) FROM users 
                    WHERE last_login >= CURRENT_DATE - INTERVAL '30 days'
                """)

                # Total searches
                total_searches = await conn.fetchval(
                    "SELECT COUNT(*) FROM search_history")

                # Searches today
                searches_today = await conn.fetchval("""
                    SELECT COUNT(*) FROM search_history 
                    WHERE DATE(searched_at) = CURRENT_DATE
                """)

            return {
                'total_users': total_users or 0,
                'active_users': active_users or 0,
                'total_searches': total_searches or 0,
                'searches_today': searches_today or 0
            }

        except Exception as e:
            logger.error(f"Get admin stats error: {e}")
            return {
                'total_users': 0,
                'active_users': 0,
                'total_searches': 0,
                'searches_today': 0
            }

    async def get_all_users(self, page: int = 1, limit: int = 50) -> Dict:
        """Get all users with pagination."""
        try:
            offset = (page - 1) * limit

            async with self.pool.acquire() as conn:
                # Get total count
                total = await conn.fetchval("SELECT COUNT(*) FROM users")

                # Get users
                users = await conn.fetch(
                    """
                    SELECT 
                        mobile, 
                        created_at, 
                        last_login,
                        (SELECT COUNT(*) FROM search_history WHERE user_mobile = users.mobile) as search_count
                    FROM users 
                    ORDER BY created_at DESC 
                    LIMIT $1 OFFSET $2
                """, limit, offset)

            return {
                'users': [dict(user) for user in users],
                'total': total,
                'page': page,
                'pages': (total + limit - 1) // limit
            }

        except Exception as e:
            logger.error(f"Get all users error: {e}")
            return {'users': [], 'total': 0, 'page': 1, 'pages': 0}


# Cache Manager
class CacheManager:

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self.redis_client = None
        self.memory_cache = {}

        if redis_url:
            try:
                self.redis_client = redis.Redis.from_url(redis_url,
                                                         decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ Redis cache connected")
            except Exception as e:
                logger.warning(
                    f"Redis connection failed, using memory cache: {e}")
                self.redis_client = None

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        try:
            if self.redis_client:
                return self.redis_client.get(key)
            else:
                return self.memory_cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set value in cache."""
        try:
            if self.redis_client:
                return self.redis_client.setex(key, ttl, value)
            else:
                self.memory_cache[key] = value
                return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching pattern."""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                keys_to_delete = [
                    k for k in self.memory_cache.keys()
                    if fnmatch.fnmatch(k, pattern)
                ]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                return len(keys_to_delete)
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        stats = {
            'memory_entries': len(self.memory_cache),
            'redis_configured': bool(self.redis_url),
            'redis_connected': bool(self.redis_client),
            'type': 'redis' if self.redis_client else 'memory'
        }

        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats.update({
                    'redis_memory':
                    info.get('used_memory_human', 'unknown'),
                    'redis_keys':
                    info.get('keyspace_hits', 0) +
                    info.get('keyspace_misses', 0),
                    'redis_hits':
                    info.get('keyspace_hits', 0),
                    'redis_misses':
                    info.get('keyspace_misses', 0)
                })
            except Exception:
                stats['redis_connected'] = False

        return stats


# Rate Limiter
class AdvancedRateLimiter:

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.memory_store = defaultdict(list)

    async def is_allowed(self, identifier: str, limit: int,
                         window: int) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        key = f"rate_limit:{identifier}"

        if self.redis:
            return await self._redis_rate_limit(key, limit, window, now,
                                                identifier)
        else:
            return self._memory_rate_limit(identifier, limit, window, now)

    async def _redis_rate_limit(self, key: str, limit: int, window: int,
                                now: float, identifier: str) -> bool:
        """Redis-based rate limiting using sliding window."""
        try:
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window)
            results = pipe.execute()

            current_requests = results[1]
            return current_requests < limit

        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            return True  # Allow on error

    def _memory_rate_limit(self, identifier: str, limit: int, window: int,
                           now: float) -> bool:
        """Memory-based rate limiting."""
        requests = self.memory_store[identifier]

        # Remove old requests
        cutoff = now - window
        self.memory_store[identifier] = [
            req_time for req_time in requests if req_time > cutoff
        ]

        # Check limit
        if len(self.memory_store[identifier]) >= limit:
            return False

        # Add current request
        self.memory_store[identifier].append(now)
        return True


# Initialize components
db = EnhancedDatabaseManager(config.POSTGRES_DSN)
cache_manager = CacheManager(config.REDIS_URL)
login_limiter = AdvancedRateLimiter(cache_manager.redis_client)

# Initialize Razorpay Lending if configured
razorpay_key = os.getenv("RAZORPAY_KEY_ID")
razorpay_secret = os.getenv("RAZORPAY_KEY_SECRET")
is_production = os.getenv("RAZORPAY_ENVIRONMENT", "test") == "live"

if razorpay_key and razorpay_secret:
    razorpay_lending_client = RazorpayLendingClient(razorpay_key,
                                                    razorpay_secret,
                                                    is_production)
    loan_manager = LoanManager(razorpay_lending_client, db)
else:
    razorpay_lending_client = None
    loan_manager = None


# GST API Client
class GSTAPIClient:

    def __init__(self, api_key: str, host: str):
        self.api_key = api_key
        self.host = host
        self.headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": host,
            "User-Agent": "GST-Intelligence-Platform/2.0"
        }

    async def fetch_gstin_data(self, gstin: str) -> Dict:
        """Fetch GSTIN data from API."""
        try:
            if not DataValidator.validate_gstin(gstin):
                raise ValueError("Invalid GSTIN format")

            # Check cache first
            cache_key = f"gstin:{gstin}"
            cached_data = await cache_manager.get(cache_key)

            if cached_data:
                return json.loads(cached_data)

            # Fetch from API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"https://{self.host}/gst",
                                            headers=self.headers,
                                            params={"gstin": gstin})

                if response.status_code == 200:
                    data = response.json()

                    # Cache the response
                    await cache_manager.set(cache_key,
                                            json.dumps(data),
                                            ttl=3600)

                    return data
                else:
                    raise HTTPException(status_code=response.status_code,
                                        detail="API request failed")

        except Exception as e:
            logger.error(f"GST API error: {e}")
            raise HTTPException(status_code=500,
                                detail="Failed to fetch GST data")


# Initialize API client
if config.RAPIDAPI_KEY:
    api_client = GSTAPIClient(config.RAPIDAPI_KEY, config.RAPIDAPI_HOST)
else:
    api_client = None


# Utility functions
def calculate_compliance_score(company_data: Dict) -> float:
    """Calculate compliance score based on company data."""
    score = 100.0

    try:
        # Check filing status
        if company_data.get('filing_status') == 'Non-Filer':
            score -= 30
        elif company_data.get('filing_status') == 'Irregular':
            score -= 15

        # Check business status
        if company_data.get('business_status') != 'Active':
            score -= 20

        # Check last filing date
        last_filing = company_data.get('last_filing_date')
        if last_filing:
            try:
                filing_date = datetime.strptime(last_filing, '%Y-%m-%d')
                days_since_filing = (datetime.now() - filing_date).days

                if days_since_filing > 90:
                    score -= 25
                elif days_since_filing > 60:
                    score -= 15
                elif days_since_filing > 30:
                    score -= 10
            except:
                score -= 5

        # Ensure score is within bounds
        return max(0.0, min(100.0, score))

    except Exception as e:
        logger.error(f"Compliance score calculation error: {e}")
        return 50.0  # Default score


def generate_pdf_report(company_data: Dict,
                        compliance_score: float,
                        synopsis: str = None,
                        late_filing_analysis: Dict = None) -> BytesIO:
    """Generate PDF report."""
    if not HAS_WEASYPRINT:
        raise HTTPException(status_code=503,
                            detail="PDF generation not available")

    try:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>GST Compliance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; }}
                .score {{ font-size: 24px; font-weight: bold; color: {'#28a745' if compliance_score >= 70 else '#ffc107' if compliance_score >= 50 else '#dc3545'}; }}
                .section {{ margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>GST Compliance Report</h1>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <div class="section">
                <h2>Company Information</h2>
                <p><strong>GSTIN:</strong> {company_data.get('gstin', 'N/A')}</p>
                <p><strong>Legal Name:</strong> {company_data.get('legal_name', 'N/A')}</p>
                <p><strong>Trade Name:</strong> {company_data.get('trade_name', 'N/A')}</p>
                <p><strong>Status:</strong> {company_data.get('business_status', 'N/A')}</p>
            </div>

            <div class="section">
                <h2>Compliance Score</h2>
                <p class="score">{compliance_score:.1f}/100</p>
            </div>

            {f'<div class="section"><h2>AI Synopsis</h2><p>{synopsis}</p></div>' if synopsis else ''}

            <div class="section">
                <h2>Report Details</h2>
                <p>This report is generated based on publicly available GST data and should be used for informational purposes only.</p>
            </div>
        </body>
        </html>
        """

        pdf = HTML(string=html_content).write_pdf()
        return BytesIO(pdf)

    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF")


# Error handler decorator
def handle_api_errors(func):

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API error in {func.__name__}: {e}")
            raise HTTPException(status_code=500,
                                detail="Internal server error")

    return wrapper


# Authentication functions
async def get_current_user(request: Request) -> Optional[str]:
    """Get current user from session."""
    token = request.cookies.get("session_token")
    if not token:
        return None

    return await db.get_user_from_session(token)


async def require_auth(request: Request) -> str:
    """Require authentication."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_admin(request: Request) -> str:
    """Require admin authentication."""
    user = await require_auth(request)

    # Check if user is admin
    admin_users = config.get_admin_users_list()
    if user not in admin_users:
        raise HTTPException(status_code=403, detail="Admin access required")

    return user


def require_role(role: UserRole):
    """Require specific role."""

    async def role_checker(request: Request) -> str:
        return await require_admin(
            request) if role == UserRole.ADMIN else await require_auth(request)

    return role_checker


async def get_user_display_name(mobile: str) -> str:
    """Get user display name."""
    return f"User {mobile[-4:]}"  # Show last 4 digits


def add_template_context(request: Request,
                         current_user: str = None,
                         **kwargs) -> Dict:
    """Add common template context."""
    context = {"request": request, "current_user": current_user, **kwargs}
    return context


# Initialize FastAPI app
app = FastAPI(title="GST Intelligence Platform",
              version="2.0.0",
              description="Advanced GST Compliance Analytics Platform")


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers[
        "Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response


@app.on_event("startup")
async def startup_event():
    """Initialize security components on startup."""
    await db.initialize()
    await db.create_tables()
    logger.info("🔐 Security system initialized")
    app.start_time = time.time()


# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Main Routes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        async with db.pool.acquire() as conn:
            await conn.execute("SELECT 1")

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "checks": {
                "database": "healthy",
                "gst_api": "configured" if config.RAPIDAPI_KEY else "missing",
                "ai_features":
                "configured" if config.ANTHROPIC_API_KEY else "disabled",
                "cache": "redis" if cache_manager.redis_client else "memory"
            }
        }
    except Exception as e:
        return JSONResponse(status_code=503,
                            content={
                                "status": "unhealthy",
                                "error": str(e),
                                "timestamp": datetime.now().isoformat()
                            })


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request,
                    current_user: str = Depends(require_auth)):
    """Main dashboard page."""
    history = await db.get_search_history(current_user)
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)

    # Calculate recent activity
    now = datetime.now()
    last_30_days = now - timedelta(days=30)
    searches_this_month = sum(
        1 for item in history
        if item.get('searched_at') and item['searched_at'] >= last_30_days)

    context = add_template_context(request=request,
                                   current_user=current_user,
                                   user_display_name=user_display_name,
                                   user_profile=user_profile,
                                   history=history,
                                   searches_this_month=searches_this_month)

    return templates.TemplateResponse("index.html", context)


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request,
                          current_user: str = Depends(require_admin)):
    """Admin dashboard page."""
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)

    return templates.TemplateResponse(
        "admin_dashboard.html", {
            "request": request,
            "current_user": current_user,
            "user_display_name": user_display_name,
            "user_profile": user_profile
        })


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    # Check if user is already logged in
    current_user = await get_current_user(request)
    if current_user:
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        "login.html", {
            "request": request,
            "current_user": None,
            "user_display_name": None,
            "user_profile": None
        })


@app.post("/login")
async def login(request: Request,
                mobile: str = Form(...),
                password: str = Form(...)):
    """Handle login."""
    client_ip = request.client.host
    is_allowed = await login_limiter.is_allowed(f"login:{client_ip}", 5,
                                                900)  # 5 attempts per 15 min

    if not is_allowed:
        return templates.TemplateResponse(
            "login.html", {
                "request": request,
                "error": "Too many login attempts. Please try again later."
            })

    if not await db.verify_user(mobile, password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials"
        })

    session_token = await db.create_session(mobile)
    if not session_token:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Failed to create session"
        })

    await db.update_last_login(mobile)

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="session_token",
                        value=session_token,
                        max_age=config.SESSION_DURATION,
                        httponly=True,
                        samesite="lax",
                        secure=config.SESSION_SECURE)
    return response


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Signup page."""
    # Check if user is already logged in
    current_user = await get_current_user(request)
    if current_user:
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        "signup.html", {
            "request": request,
            "current_user": None,
            "user_display_name": None,
            "user_profile": None
        })


@app.post("/signup")
async def signup(request: Request,
                 mobile: str = Form(...),
                 password: str = Form(...),
                 confirm_password: str = Form(...)):
    """Handle signup."""
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Passwords do not match"
        })

    if not DataValidator.validate_mobile(mobile):
        return templates.TemplateResponse(
            "signup.html", {
                "request": request,
                "error": "Invalid mobile number format"
            })

    if len(password) < 8:
        return templates.TemplateResponse(
            "signup.html", {
                "request": request,
                "error": "Password must be at least 8 characters long"
            })

    success = await db.create_user(mobile, password)
    if not success:
        return templates.TemplateResponse(
            "signup.html", {
                "request": request,
                "error": "User already exists or registration failed"
            })

    return RedirectResponse(url="/login?registered=true", status_code=302)


@app.get("/logout")
async def logout():
    """Handle logout."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request,
                       current_user: str = Depends(require_auth)):
    """Search history page."""
    history = await db.get_all_searches(current_user)
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)

    # Calculate recent activity
    now = datetime.now()
    last_30_days = now - timedelta(days=30)
    searches_this_month = sum(
        1 for item in history
        if item.get('searched_at') and item['searched_at'] >= last_30_days)

    return templates.TemplateResponse(
        "history.html", {
            "request": request,
            "current_user": current_user,
            "user_display_name": user_display_name,
            "user_profile": user_profile,
            "history": history,
            "searches_this_month": searches_this_month
        })


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request,
                         current_user: str = Depends(require_auth)):
    """Analytics dashboard page."""
    try:
        user_profile = await db.get_user_profile(current_user)
        user_display_name = await get_user_display_name(current_user)

        # Get analytics data with better error handling
        try:
            analytics_data = await db.get_analytics_data(current_user)
        except Exception as e:
            logger.error(f"Analytics data error: {e}")
            analytics_data = {
                "daily_searches": [],
                "score_distribution": [],
                "top_companies": []
            }

        # Get overall stats
        try:
            stats = await db.get_user_stats(current_user)
        except Exception as e:
            logger.error(f"User stats error: {e}")
            stats = {
                "total_searches": 0,
                "unique_companies": 0,
                "avg_compliance": 0,
                "recent_searches": 0
            }

        # Calculate recent activity
        now = datetime.now()
        last_30_days = now - timedelta(days=30)

        # Get history for recent searches calculation
        try:
            history = await db.get_search_history(current_user)
            searches_this_month = sum(1 for item in history
                                      if item.get('searched_at')
                                      and item['searched_at'] >= last_30_days)
        except Exception as e:
            logger.error(f"History data error: {e}")
            searches_this_month = 0

        return templates.TemplateResponse(
            "analytics.html",
            {
                "request": request,
                "current_user": current_user,
                "user_display_name": user_display_name,
                "user_profile": user_profile,
                "analytics_data": analytics_data,
                "stats": stats,
                "searches_this_month": searches_this_month,
                **analytics_data  # Unpack analytics data for direct access in template
            })

    except Exception as e:
        logger.error(f"Analytics page error: {e}")
        return templates.TemplateResponse(
            "analytics.html", {
                "request": request,
                "current_user": current_user,
                "user_display_name": await get_user_display_name(current_user),
                "user_profile": {},
                "analytics_data": {
                    "daily_searches": [],
                    "score_distribution": [],
                    "top_companies": []
                },
                "stats": {
                    "total_searches": 0,
                    "unique_companies": 0,
                    "avg_compliance": 0,
                    "recent_searches": 0
                },
                "searches_this_month": 0,
                "daily_searches": [],
                "score_distribution": [],
                "top_companies": [],
                "error": "Failed to load analytics data"
            })


# API Routes
@app.post("/api/search")
@handle_api_errors
async def search_gstin(request: Request,
                       gstin: str = Form(...),
                       current_user: str = Depends(require_auth)):
    """Search GSTIN and return company data."""
    try:
        if not api_client:
            raise HTTPException(status_code=503,
                                detail="GST API service not configured")

        # Validate GSTIN
        if not DataValidator.validate_gstin(gstin):
            raise HTTPException(status_code=400, detail="Invalid GSTIN format")

        # Fetch data
        company_data = await api_client.fetch_gstin_data(gstin)
        compliance_score = calculate_compliance_score(company_data)

        # Save search history
        await db.save_search(current_user, gstin,
                             company_data.get('legal_name', 'Unknown'),
                             compliance_score, company_data)

        # Get AI synopsis if available
        synopsis = None
        if config.ANTHROPIC_API_KEY:
            try:
                synopsis = await get_anthropic_synopsis(company_data)
            except Exception as e:
                logger.error(f"AI synopsis error: {e}")
                synopsis = "AI synopsis temporarily unavailable"

        return {
            "success": True,
            "data": {
                **company_data, "compliance_score": compliance_score,
                "ai_synopsis": synopsis
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@app.get("/api/admin/stats")
@handle_api_errors
async def get_admin_stats(current_user: str = Depends(require_admin)):
    """Get admin statistics."""
    return await db.get_admin_stats()


@app.get("/api/admin/users")
@handle_api_errors
async def get_admin_users(page: int = 1,
                          current_user: str = Depends(require_admin)):
    """Get all users for admin."""
    return await db.get_all_users(page)


@app.get("/api/cache/stats")
@handle_api_errors
async def get_cache_stats(current_user: str = Depends(require_auth)):
    """Get cache statistics."""
    try:
        if cache_manager.redis_client:
            info = cache_manager.redis_client.info()
            return {
                'success': True,
                'cache_type': 'redis',
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses')
            }
        else:
            return {
                'success':
                True,
                'cache_type':
                'memory',
                'entries':
                len(cache_manager.memory_cache),
                'memory_usage':
                f"{len(str(cache_manager.memory_cache))} bytes (approx)"
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.delete("/api/admin/cache/clear")
@handle_api_errors
async def clear_cache(pattern: str = "*",
                      current_user: str = Depends(require_admin)):
    """Clear cache entries by pattern."""
    try:
        count = await cache_manager.clear_pattern(pattern)
        return {'success': True, 'cleared_count': count, 'pattern': pattern}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# Export and PDF Routes
@app.get("/export/history")
async def export_history(current_user: str = Depends(require_auth)):
    """Export search history as CSV."""
    try:
        history = await db.get_all_searches(current_user)
        output = StringIO()
        writer = csv.DictWriter(output,
                                fieldnames=[
                                    'searched_at', 'gstin', 'company_name',
                                    'compliance_score'
                                ])
        writer.writeheader()

        for item in history:
            writer.writerow({
                'searched_at':
                item['searched_at'].isoformat() if item['searched_at'] else '',
                'gstin':
                item['gstin'],
                'company_name':
                item['company_name'],
                'compliance_score':
                item['compliance_score'] if item['compliance_score'] else ''
            })

        content = output.getvalue()
        output.close()

        return StreamingResponse(
            BytesIO(content.encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                f"attachment; filename=gst_search_history_{datetime.now().strftime('%Y%m%d')}.csv"
            })
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail="Export failed")


@app.post("/generate-pdf")
async def generate_pdf_route(request: Request,
                             gstin: str = Form(...),
                             current_user: str = Depends(require_auth)):
    """Generate PDF report."""
    if not HAS_WEASYPRINT:
        raise HTTPException(status_code=503,
                            detail="PDF generation not available")

    try:
        if not api_client:
            raise HTTPException(status_code=503,
                                detail="GST API service not configured")

        company_data = await api_client.fetch_gstin_data(gstin)
        compliance_score = calculate_compliance_score(company_data)

        synopsis = None
        if config.ANTHROPIC_API_KEY:
            try:
                synopsis = await get_anthropic_synopsis(company_data)
            except:
                synopsis = "AI synopsis not available"

        pdf_content = generate_pdf_report(company_data, compliance_score,
                                          synopsis)

        return StreamingResponse(
            pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                f"attachment; filename=GST_Report_{gstin}.pdf"
            })

    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF")


# Loan Management Routes (if enabled)
@app.post("/api/loans/apply")
@handle_api_errors
async def apply_for_loan(request: LoanApplicationRequest,
                         current_user: str = Depends(require_auth)):
    """Apply for a business loan"""
    try:
        if not loan_manager:
            return JSONResponse(status_code=503,
                                content={
                                    "success": False,
                                    "error": "Loan service not available"
                                })

        # Validate application data
        application_data = request.dict()
        is_valid, message = LoanConfig.validate_loan_application(
            application_data)

        if not is_valid:
            return JSONResponse(status_code=400,
                                content={
                                    "success": False,
                                    "error": message
                                })

        # Submit loan application
        result = await loan_manager.submit_loan_application(
            current_user, application_data)

        if result["success"]:
            return {
                "success": True,
                "data": result,
                "message": "Loan application submitted successfully"
            }
        else:
            return JSONResponse(status_code=400,
                                content={
                                    "success":
                                    False,
                                    "error":
                                    result.get("error", "Application failed")
                                })

    except Exception as e:
        logger.error(f"Loan application error: {e}")
        return JSONResponse(status_code=500,
                            content={
                                "success": False,
                                "error": "Loan application failed"
                            })


# Static file routes
@app.get("/favicon.ico")
async def favicon():
    """Favicon route."""
    # Simple 1x1 PNG favicon
    favicon_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x00\x01\x8d\xc8\x02\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(content=favicon_bytes, media_type="image/png")


@app.get("/manifest.json")
async def get_manifest():
    """PWA manifest route."""
    with open("static/manifest.json", "r") as f:
        manifest_content = f.read()
    return Response(content=manifest_content, media_type="application/json")


@app.get("/sw.js")
async def get_service_worker():
    """Service worker route."""
    with open("sw.js", "r") as f:
        sw_content = f.read()
    return Response(content=sw_content, media_type="application/javascript")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app",
                host=config.HOST,
                port=config.PORT,
                reload=config.DEBUG,
                log_level="info")
