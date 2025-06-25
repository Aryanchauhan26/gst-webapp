#!/usr/bin/env python3
"""
GST Intelligence Platform - Main Application (CLEANED & OPTIMIZED)
Enhanced with loan management and duplicate code removed
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
import redis
import fnmatch
import csv
from datetime import datetime, timedelta
from functools import wraps
from decimal import Decimal
from collections import defaultdict
from typing import Optional, Dict, List, Any
from io import BytesIO

# FastAPI imports
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# External libraries
from dotenv import load_dotenv
from pydantic import BaseModel, validator

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try importing optional dependencies with better error handling
try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
    logger.info("WeasyPrint available - PDF generation enabled")
except (ImportError, OSError, Exception) as e:
    logging.warning(f"WeasyPrint not available - PDF generation disabled: {e}")
    HAS_WEASYPRINT = False
    HTML = None

# Local imports
try:
    from razorpay_lending import RazorpayLendingClient, LoanManager, LoanConfig, LoanStatus
    HAS_LOAN_MANAGEMENT = True
except ImportError:
    logging.warning("Loan management not available")
    HAS_LOAN_MANAGEMENT = False
    LoanConfig = None
    LoanStatus = None

from anthro_ai import get_anthropic_synopsis
from config import settings

# Load environment variables
load_dotenv()

config = settings

# =============================================================================
# PYDANTIC MODELS (Consolidated)
# =============================================================================

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
    
    @validator('loan_amount', 'annual_turnover', 'monthly_revenue')
    def validate_positive_amounts(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v
    
    @validator('tenure_months', 'business_vintage_months')
    def validate_positive_months(cls, v):
        if v <= 0:
            raise ValueError('Months must be positive')
        return v
    
    @validator('compliance_score')
    def validate_compliance_score(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Compliance score must be between 0 and 100')
        return v

class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str
    
    @validator('newPassword')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserPreferencesRequest(BaseModel):
    emailNotifications: Optional[bool] = False
    pushNotifications: Optional[bool] = False
    autoSearch: Optional[bool] = True
    animations: Optional[bool] = True
    compactMode: Optional[bool] = False
    saveHistory: Optional[bool] = True
    analytics: Optional[bool] = True

class UserProfileRequest(BaseModel):
    display_name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    designation: Optional[str] = None

class BatchSearchRequest(BaseModel):
    gstins: List[str]
    
    @validator('gstins')
    def validate_gstins(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 GSTINs allowed')
        return v

class ErrorLogRequest(BaseModel):
    type: str
    message: str
    stack: Optional[str] = None
    url: Optional[str] = None
    userAgent: Optional[str] = None
    timestamp: Optional[str] = None

# =============================================================================
# ERROR HANDLING DECORATOR (Consolidated)
# =============================================================================

def handle_api_errors(func):
    """Decorator for handling API errors consistently"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API error in {func.__name__}: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Internal server error"}
            )
    return wrapper

# =============================================================================
# CACHE MANAGER (Fixed)
# =============================================================================

class CacheManager:
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache manager with Redis fallback to in-memory."""
        self.redis_client = None
        self.memory_cache = {}
        self.cache_ttl = 300
        self._cleanup_task = None
        
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info("✅ Redis cache initialized")
            except Exception as e:
                logger.warning(f"Redis unavailable, using memory cache: {e}")
        
        if not self.redis_client:
            self._cleanup_task = asyncio.create_task(self._cleanup_memory_cache())
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value.decode('utf-8'))
            else:
                if key in self.memory_cache:
                    data, timestamp = self.memory_cache[key]
                    if datetime.now().timestamp() - timestamp < self.cache_ttl:
                        return data
                    else:
                        del self.memory_cache[key]
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            ttl = ttl or self.cache_ttl
            serialized_value = json.dumps(value)
            
            if self.redis_client:
                self.redis_client.setex(key, ttl, serialized_value)
            else:
                self.memory_cache[key] = (value, datetime.now().timestamp())
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                self.memory_cache.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        try:
            count = 0
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    count = self.redis_client.delete(*keys)
            else:
                keys_to_delete = [k for k in self.memory_cache.keys() if fnmatch.fnmatch(k, pattern)]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                count = len(keys_to_delete)
            return count
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0
    
    async def close(self):
        """Properly cleanup resources"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_memory_cache(self):
        """Periodic cleanup of expired memory cache entries."""
        while True:
            try:
                await asyncio.sleep(60)
                current_time = datetime.now().timestamp()
                expired_keys = [
                    key for key, (_, timestamp) in self.memory_cache.items()
                    if current_time - timestamp > self.cache_ttl
                ]
                for key in expired_keys:
                    del self.memory_cache[key]
                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                break

# =============================================================================
# RATE LIMITER (Fixed)
# =============================================================================

class RateLimiter:
    def __init__(self, max_requests: int = config.RATE_LIMIT_REQUESTS, 
                 window_seconds: int = config.RATE_LIMIT_WINDOW):
        self.requests = defaultdict(list)
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self._last_cleanup = datetime.now()
        self._cleanup_interval = timedelta(hours=1)
    
    def is_allowed(self, identifier: str) -> bool:
        now = datetime.now()
        
        # Clean up old entries periodically to prevent memory leaks
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_entries(now)
            self._last_cleanup = now
        
        # Clean recent requests for this identifier
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < self.window
        ]
        
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        
        self.requests[identifier].append(now)
        return True
    
    def _cleanup_old_entries(self, now: datetime):
        """Remove old entries to prevent memory leaks"""
        cutoff = now - self.window
        for identifier in list(self.requests.keys()):
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > cutoff
            ]
            if not self.requests[identifier]:
                del self.requests[identifier]

# =============================================================================
# DATABASE MANAGER (Optimized)
# =============================================================================

class DatabaseManager:
    def __init__(self, dsn: str = config.POSTGRES_DSN):
        self.dsn = dsn
        self.pool = None

    async def initialize(self):
        """Initialize database connection pool and ensure tables exist."""
        if not self.pool:
            pool_min_size = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
            pool_max_size = int(os.getenv("DB_POOL_MAX_SIZE", "10"))
            self.pool = await asyncpg.create_pool(
                dsn=self.dsn, 
                min_size=pool_min_size, 
                max_size=pool_max_size
            )
        await self._ensure_tables()

    async def _ensure_tables(self):
        """Ensure all required tables exist."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    mobile VARCHAR(10) PRIMARY KEY,
                    password_hash VARCHAR(128) NOT NULL,
                    salt VARCHAR(32) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token VARCHAR(64) PRIMARY KEY,
                    mobile VARCHAR(10) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    mobile VARCHAR(10) NOT NULL,
                    gstin VARCHAR(15) NOT NULL,
                    company_name TEXT NOT NULL,
                    compliance_score DECIMAL(5,2),
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS user_preferences (
                    mobile VARCHAR(10) PRIMARY KEY,
                    preferences JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
                CREATE INDEX IF NOT EXISTS idx_search_history_mobile ON search_history(mobile);
                CREATE INDEX IF NOT EXISTS idx_search_history_searched_at ON search_history(searched_at);
                CREATE INDEX IF NOT EXISTS idx_user_preferences_mobile ON user_preferences(mobile);
            """)

    async def create_user(self, mobile: str, password_hash: str, salt: str) -> bool:
        """Create a new user."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO users (mobile, password_hash, salt) VALUES ($1, $2, $3)",
                    mobile, password_hash, salt
                )
                return True
        except asyncpg.UniqueViolationError:
            return False

    async def verify_user(self, mobile: str, password: str) -> bool:
        """Verify user credentials."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT password_hash, salt FROM users WHERE mobile=$1", mobile
            )
            if not row:
                return False
            return self._check_password(password, row['password_hash'], row['salt'])

    async def change_password(self, mobile: str, old_password: str, new_password: str) -> bool:
        """Change user password after verifying old password."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT password_hash, salt FROM users WHERE mobile=$1", mobile)
            if not row or not self._check_password(old_password, row['password_hash'], row['salt']):
                return False
            
            new_salt = secrets.token_hex(16)
            new_hash = hashlib.pbkdf2_hmac('sha256', new_password.encode('utf-8'), new_salt.encode('utf-8'), 100000, dklen=64).hex()
            
            await conn.execute(
                "UPDATE users SET password_hash=$1, salt=$2 WHERE mobile=$3",
                new_hash, new_salt, mobile
            )
            return True

    async def create_session(self, mobile: str) -> Optional[str]:
        """Create a new session for user."""
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + config.SESSION_DURATION
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO sessions (session_token, mobile, expires_at) VALUES ($1, $2, $3)",
                    session_token, mobile, expires_at
                )
            return session_token
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None

    async def get_session(self, session_token: str) -> Optional[str]:
        """Get user from session token."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT mobile, expires_at FROM sessions WHERE session_token=$1",
                session_token
            )
            if row and row['expires_at'] > datetime.now():
                return row['mobile']
        return None

    async def delete_session(self, session_token: str):
        """Delete a session."""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM sessions WHERE session_token=$1", session_token)

    async def update_last_login(self, mobile: str):
        """Update user's last login time."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login=$1 WHERE mobile=$2", 
                datetime.now(), mobile
            )

    async def add_search_history(self, mobile: str, gstin: str, 
                               company_name: str, compliance_score: Optional[float] = None):
        """Add search to history."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM search_history 
                WHERE mobile = $1 AND id NOT IN (
                    SELECT id FROM search_history 
                    WHERE mobile = $1 
                    ORDER BY searched_at DESC 
                    LIMIT $2
                )
            """, mobile, config.MAX_SEARCH_HISTORY - 1)
            
            await conn.execute(
                "INSERT INTO search_history (mobile, gstin, company_name, compliance_score) VALUES ($1, $2, $3, $4)",
                mobile, gstin, company_name, compliance_score
            )

    async def get_search_history(self, mobile: str, limit: int = 10) -> List[Dict]:
        """Get user's search history."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT gstin, company_name, searched_at, compliance_score FROM search_history WHERE mobile=$1 ORDER BY searched_at DESC LIMIT $2",
                mobile, limit
            )
            return [dict(row) for row in rows]

    async def get_all_searches(self, mobile: str) -> List[Dict]:
        """Get all user searches for history page."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT gstin, company_name, searched_at, compliance_score FROM search_history WHERE mobile=$1 ORDER BY searched_at DESC",
                mobile
            )
            return [dict(row) for row in rows]

    async def get_user_stats(self, mobile: str) -> Dict:
        """Get comprehensive user statistics."""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_searches,
                    COUNT(DISTINCT gstin) as unique_companies,
                    AVG(compliance_score) as avg_compliance,
                    COUNT(CASE WHEN searched_at >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as recent_searches,
                    MAX(searched_at) as last_search
                FROM search_history 
                WHERE mobile = $1
            """, mobile)
            
            return {
                "total_searches": stats["total_searches"] or 0,
                "unique_companies": stats["unique_companies"] or 0,
                "avg_compliance": float(stats["avg_compliance"]) if stats["avg_compliance"] else 0,
                "recent_searches": stats["recent_searches"] or 0,
                "last_search": stats["last_search"].isoformat() if stats["last_search"] else None,
                "user_level": self._get_user_level(stats["total_searches"] or 0),
                "achievements": self._get_achievements(stats["total_searches"] or 0)
            }

    async def get_analytics_data(self, mobile: str) -> Dict:
        """Get analytics data for charts."""
        async with self.pool.acquire() as conn:
            daily_searches = await conn.fetch("""
                SELECT DATE(searched_at) as date, COUNT(*) as search_count, AVG(compliance_score) as avg_score
                FROM search_history WHERE mobile = $1 AND searched_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE(searched_at) ORDER BY date
            """, mobile)
            
            score_distribution = await conn.fetch("""
                SELECT CASE WHEN compliance_score >= 90 THEN 'Excellent (90-100)'
                            WHEN compliance_score >= 80 THEN 'Very Good (80-89)'
                            WHEN compliance_score >= 70 THEN 'Good (70-79)'
                            WHEN compliance_score >= 60 THEN 'Average (60-69)'
                            ELSE 'Poor (<60)' END as range, COUNT(*) as count
                FROM search_history WHERE mobile = $1 AND compliance_score IS NOT NULL 
                GROUP BY range ORDER BY range DESC
            """, mobile)
            
            top_companies = await conn.fetch("""
                SELECT company_name, gstin, COUNT(*) as search_count, MAX(compliance_score) as latest_score
                FROM search_history WHERE mobile = $1 GROUP BY company_name, gstin
                ORDER BY search_count DESC LIMIT 10
            """, mobile)
            
            return {
                "daily_searches": [dict(row) for row in daily_searches],
                "score_distribution": [dict(row) for row in score_distribution],
                "top_companies": [dict(row) for row in top_companies]
            }

    def _get_user_level(self, total_searches: int) -> Dict:
        """Determine user level based on activity."""
        levels = [
            (100, "Expert", "fas fa-crown", "#f59e0b"),
            (50, "Advanced", "fas fa-star", "#3b82f6"),
            (20, "Intermediate", "fas fa-chart-line", "#10b981"),
            (5, "Beginner", "fas fa-seedling", "#8b5cf6"),
            (0, "New User", "fas fa-user-plus", "#6b7280")
        ]
        
        for threshold, level, icon, color in levels:
            if total_searches >= threshold:
                return {"level": level, "icon": icon, "color": color}
        
        return {"level": levels[-1][1], "icon": levels[-1][2], "color": levels[-1][3]}

    def _get_achievements(self, total_searches: int) -> List[Dict]:
        """Get user achievements."""
        achievements = []
        
        achievement_data = [
            (1, "First Search", "Completed your first GST search", "fas fa-search"),
            (10, "Research Enthusiast", "Completed 10 searches", "fas fa-chart-bar"),
            (50, "Compliance Expert", "Completed 50 searches", "fas fa-medal"),
        ]
        
        for threshold, title, desc, icon in achievement_data:
            achievements.append({
                "title": title,
                "description": desc,
                "icon": icon,
                "unlocked": total_searches >= threshold
            })
        
        return achievements

    async def save_user_preferences(self, mobile: str, preferences: Dict):
        """Save user preferences."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_preferences (mobile, preferences, updated_at) 
                VALUES ($1, $2, $3)
                ON CONFLICT (mobile) 
                DO UPDATE SET preferences = $2, updated_at = $3
            """, mobile, json.dumps(preferences), datetime.now())

    async def get_user_preferences(self, mobile: str) -> Dict:
        """Get user preferences."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT preferences FROM user_preferences WHERE mobile = $1", mobile
            )
            return json.loads(row['preferences']) if row else {}

    async def save_user_profile(self, mobile: str, profile_data: Dict):
        """Save user profile information."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_preferences (mobile, preferences, updated_at) 
                VALUES ($1, $2, $3)
                ON CONFLICT (mobile) 
                DO UPDATE SET 
                    preferences = user_preferences.preferences || $2::jsonb,
                    updated_at = $3
            """, mobile, json.dumps(profile_data), datetime.now())

    async def get_user_profile(self, mobile: str) -> Dict:
        """Get user profile information."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT preferences FROM user_preferences WHERE mobile = $1", mobile)
            if row:
                prefs = json.loads(row['preferences'])
                return {
                    'display_name': prefs.get('display_name'),
                    'company': prefs.get('company'),
                    'email': prefs.get('email'),
                    'designation': prefs.get('designation')
                }
            return {}

    async def clear_user_data(self, mobile: str) -> int:
        """Clear user search history."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("DELETE FROM search_history WHERE mobile = $1 RETURNING COUNT(*)", mobile)
            return result or 0

    def _check_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash."""
        hash_attempt = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), 
            salt.encode('utf-8'), 100000, dklen=64
        ).hex()
        return hash_attempt == stored_hash

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM sessions WHERE expires_at < $1', datetime.now())

# =============================================================================
# GST API CLIENT (Optimized)
# =============================================================================

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
        url = f"https://{self.host}/free/gstin/{gstin}"
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and "data" in data:
                    return data["data"]
                elif "data" in data:
                    return data["data"]
                else:
                    return data
            
            raise HTTPException(
                status_code=404, 
                detail="GSTIN not found or API error"
            )

# =============================================================================
# UTILITY FUNCTIONS (Consolidated)
# =============================================================================

def validate_mobile(mobile: str) -> tuple[bool, str]:
    """Validate mobile number format."""
    mobile = mobile.strip()
    if not mobile.isdigit() or len(mobile) != 10 or mobile[0] not in "6789":
        return False, "Invalid mobile number format"
    return True, ""

def validate_gstin(gstin: str) -> bool:
    """Validate GSTIN format."""
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    return bool(re.match(pattern, gstin.upper()))

def calculate_return_due_date(return_type: str, tax_period: str, fy: str) -> Optional[datetime]:
    """Calculate due date for GST returns."""
    try:
        months = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        
        if tax_period in months:
            month = months[tax_period]
            fy_parts = fy.split('-')
            if month >= 4:
                year = int(fy_parts[0])
            else:
                year = int(fy_parts[1])
            
            if return_type == "GSTR1":
                if month == 12:
                    due_date = datetime(year + 1, 1, 11)
                else:
                    due_date = datetime(year, month + 1, 11)
            elif return_type == "GSTR3B":
                if month == 12:
                    due_date = datetime(year + 1, 1, 20)
                else:
                    due_date = datetime(year, month + 1, 20)
            elif return_type == "GSTR9":
                year = int(fy_parts[1])
                due_date = datetime(year, 12, 31)
            else:
                return None
                
            return due_date
    except:
        return None
    
    return None

def analyze_late_filings(returns: List[Dict]) -> Dict:
    """Analyze late filing patterns."""
    late_returns = []
    on_time_returns = []
    total_delay_days = 0
    
    for return_item in returns:
        return_type = return_item.get("rtntype")
        tax_period = return_item.get("taxp")
        fy = return_item.get("fy")
        dof = return_item.get("dof")
        
        if all([return_type, tax_period, fy, dof]):
            due_date = calculate_return_due_date(return_type, tax_period, fy)
            
            if due_date:
                try:
                    filing_date = datetime.strptime(dof, "%d/%m/%Y")
                    
                    if filing_date > due_date:
                        delay_days = (filing_date - due_date).days
                        late_returns.append({
                            'return': return_item,
                            'due_date': due_date,
                            'filing_date': filing_date,
                            'delay_days': delay_days
                        })
                        total_delay_days += delay_days
                    else:
                        on_time_returns.append(return_item)
                except:
                    pass
    
    return {
        'late_count': len(late_returns),
        'on_time_count': len(on_time_returns),
        'late_returns': late_returns,
        'total_delay_days': total_delay_days,
        'average_delay': total_delay_days / len(late_returns) if late_returns else 0
    }

def calculate_compliance_score(company_data: Dict) -> float:
    """Calculate compliance score based on company data."""
    score = 100.0
    
    # Registration Status (25 points)
    if company_data.get("sts") != "Active":
        score -= 25
    
    # Filing Compliance (20 points)
    returns = company_data.get("returns", [])
    if returns:
        current_date = datetime.now()
        gstr1_returns = [r for r in returns if r.get("rtntype") == "GSTR1"]
        
        months_since_reg = 12
        if company_data.get("rgdt"):
            try:
                reg_date = datetime.strptime(company_data["rgdt"], "%d/%m/%Y")
                months_since_reg = max(1, (current_date - reg_date).days // 30)
            except:
                pass
        
        expected_returns = min(months_since_reg, 12)
        filing_ratio = min(len(gstr1_returns) / expected_returns, 1.0) if expected_returns > 0 else 0
        filing_points = int(filing_ratio * 20)
        score = score - 20 + filing_points
    else:
        score -= 20
    
    # Late Filing Analysis (25 points)
    if returns:
        late_filing_analysis = analyze_late_filings(returns)
        late_count = late_filing_analysis['late_count']
        total_returns = late_count + late_filing_analysis['on_time_count']
        
        if total_returns > 0:
            on_time_ratio = late_filing_analysis['on_time_count'] / total_returns
            late_filing_points = int(on_time_ratio * 25)
            
            avg_delay = late_filing_analysis['average_delay']
            if avg_delay > 30:
                late_filing_points = max(0, late_filing_points - 5)
            
            score = score - 25 + late_filing_points
        else:
            score -= 13
        
        company_data['_late_filing_analysis'] = late_filing_analysis
    else:
        score -= 25
    
    # Filing Recency (15 points)
    if returns:
        latest_return_date = None
        for return_item in returns:
            if return_item.get("dof"):
                try:
                    dof = datetime.strptime(return_item["dof"], "%d/%m/%Y")
                    if not latest_return_date or dof > latest_return_date:
                        latest_return_date = dof
                except:
                    pass
        
        if latest_return_date:
            days_since_filing = (current_date - latest_return_date).days
            if days_since_filing <= 30:
                recency_points = 15
            elif days_since_filing <= 60:
                recency_points = 10
            elif days_since_filing <= 90:
                recency_points = 5
            else:
                recency_points = 0
            
            score = score - 15 + recency_points
    else:
        score -= 15
    
    # Filing Frequency (5 points)
    filing_freq = company_data.get("fillingFreq", {})
    if filing_freq:
        monthly_count = sum(1 for freq in filing_freq.values() if freq == "M")
        quarterly_count = sum(1 for freq in filing_freq.values() if freq == "Q")
        
        if monthly_count >= 6:
            freq_points = 5
        elif quarterly_count >= 6:
            freq_points = 4
        else:
            freq_points = 2
        
        score = score - 5 + freq_points
    else:
        score -= 3
    
    # E-Invoice & Annual Returns (5 points each)
    einvoice = company_data.get("einvoiceStatus", "No")
    if einvoice != "Yes":
        score -= 3
    
    annual_returns = [r for r in returns if r.get("rtntype") == "GSTR9"]
    if not annual_returns:
        score -= 5
    
    final_score = max(0, min(100, score))
    logger.info(f"Calculated compliance score: {final_score} for company {company_data.get('lgnm', 'Unknown')}")
    return final_score

async def get_cached_gstin_data(gstin: str) -> Optional[Dict]:
    """Get GSTIN data from cache first, then API."""
    cache_key = f"gstin:{gstin}"
    
    cached_data = await cache_manager.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for GSTIN: {gstin}")
        return cached_data
    
    if api_client:
        try:
            company_data = await api_client.fetch_gstin_data(gstin)
            await cache_manager.set(cache_key, company_data, ttl=3600)
            logger.info(f"Cached GSTIN data: {gstin}")
            return company_data
        except Exception as e:
            logger.error(f"API fetch failed for {gstin}: {e}")
            raise
    
    return None

async def get_user_display_name(mobile: str) -> str:
    """Get user display name or fallback to mobile."""
    try:
        profile = await db.get_user_profile(mobile)
        display_name = profile.get('display_name')
        if display_name:
            return display_name
        return f"User {mobile[-4:]}"
    except:
        return f"User {mobile[-4:]}"

# =============================================================================
# AUTHENTICATION (Consolidated)
# =============================================================================

async def get_current_user(request: Request) -> Optional[str]:
    """Get current user from session."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    return await db.get_session(session_token)

async def get_current_user_or_raise(request: Request, admin_required: bool = False) -> str:
    """Unified auth check with optional admin requirement"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )
    
    if admin_required:
        admin_users = os.getenv("ADMIN_USERS", "").split(",")
        if user not in admin_users:
            raise HTTPException(status_code=403, detail="Admin access required")
    
    return user

async def require_auth(request: Request) -> str:
    """Require authentication for protected routes."""
    return await get_current_user_or_raise(request)

async def require_admin(request: Request) -> str:
    """Require admin authentication."""
    return await get_current_user_or_raise(request, admin_required=True)

# =============================================================================
# INITIALIZE FASTAPI APP
# =============================================================================

app = FastAPI(
    title="GST Intelligence Platform", 
    version="2.0.0",
    description="Advanced GST Compliance Analytics Platform"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize components
db = DatabaseManager()
cache_manager = CacheManager(os.getenv("REDIS_URL"))
login_limiter = RateLimiter(max_requests=5, window_seconds=900)
api_limiter = RateLimiter()

# Initialize API client
api_client = GSTAPIClient(config.RAPIDAPI_KEY, config.RAPIDAPI_HOST) if config.RAPIDAPI_KEY else None

# Initialize loan manager
loan_manager = None
if HAS_LOAN_MANAGEMENT and config.RAZORPAY_KEY_ID and config.RAZORPAY_KEY_SECRET:
    try:
        razorpay_client = RazorpayLendingClient(
            key_id=config.RAZORPAY_KEY_ID,
            key_secret=config.RAZORPAY_KEY_SECRET,
            environment=config.RAZORPAY_ENVIRONMENT
        )
        loan_manager = LoanManager(razorpay_client, db)
        logger.info("✅ Loan management system initialized")
    except Exception as e:
        logger.error(f"Failed to initialize loan management: {e}")

# =============================================================================
# MAIN ROUTES
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "checks": {
                "database": "healthy",
                "gst_api": "configured" if config.RAPIDAPI_KEY else "missing",
                "ai_features": "configured" if config.ANTHROPIC_API_KEY else "disabled",
                "cache": "redis" if cache_manager.redis_client else "memory",
                "loan_management": "available" if HAS_LOAN_MANAGEMENT else "disabled"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e), 
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: str = Depends(require_auth)):
    """Main dashboard page."""
    history = await db.get_search_history(current_user)
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)
    
    now = datetime.now()
    last_30_days = now - timedelta(days=30)
    searches_this_month = sum(
        1 for item in history
        if item.get('searched_at') and item['searched_at'] >= last_30_days
    )
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_user": current_user,
        "user_display_name": user_display_name,
        "user_profile": user_profile,
        "history": history,
        "searches_this_month": searches_this_month
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, mobile: str = Form(...), password: str = Form(...)):
    """Handle login."""
    is_valid, message = validate_mobile(mobile)
    if not is_valid:
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": message
        })
    
    if not login_limiter.is_allowed(mobile):
        return templates.TemplateResponse("login.html", {
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
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=int(config.SESSION_DURATION.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=False
    )
    return response

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Signup page."""
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(request: Request, mobile: str = Form(...), 
                password: str = Form(...), confirm_password: str = Form(...)):
    """Handle signup."""
    is_valid, message = validate_mobile(mobile)
    if not is_valid:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": message
        })
    
    if len(password) < 6:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Password must be at least 6 characters"
        })
    
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Passwords do not match"
        })
    
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), 
        salt.encode('utf-8'), 100000, dklen=64
    ).hex()
    
    success = await db.create_user(mobile, password_hash, salt)
    if not success:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Mobile number already registered"
        })
    
    return RedirectResponse(url="/login?registered=true", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    """Handle logout."""
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.delete_session(session_token)
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response

# =============================================================================
# SEARCH ROUTES (Optimized)
# =============================================================================

@app.get("/search")
async def search_gstin_get(request: Request, gstin: str = None, current_user: str = Depends(require_auth)):
    """Handle GET search requests."""
    if not gstin:
        return RedirectResponse(url="/", status_code=302)
    
    return await process_search(request, gstin, current_user)

@app.post("/search")
async def search_gstin_post(request: Request, gstin: str = Form(...), current_user: str = Depends(require_auth)):
    """Handle POST search requests."""
    return await process_search(request, gstin, current_user)

async def process_search(request: Request, gstin: str, current_user: str):
    """Process GST search request."""
    gstin = gstin.strip().upper()
    if not validate_gstin(gstin):
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "current_user": current_user, 
            "error": "Invalid GSTIN format", 
            "history": history
        })
    
    if not api_limiter.is_allowed(current_user):
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "current_user": current_user, 
            "error": "API rate limit exceeded. Please try again later.", 
            "history": history
        })
    
    try:
        if not api_client:
            raise HTTPException(status_code=503, detail="GST API service not configured")
            
        company_data = await get_cached_gstin_data(gstin)
        if not company_data:
            raise HTTPException(status_code=503, detail="GST API service not available")
        
        compliance_score = calculate_compliance_score(company_data)
        logger.info(f"Final compliance score for template: {compliance_score}")
        
        synopsis = None
        if config.ANTHROPIC_API_KEY:
            try:
                from anthro_ai import CompanyAnalyzer
                
                analyzer = CompanyAnalyzer(config.ANTHROPIC_API_KEY)
                
                company_name = company_data.get("lgnm", "")
                location = None
                if company_data.get('stj') and 'State - ' in str(company_data.get('stj')):
                    try:
                        location = company_data['stj'].split('State - ')[1].split(',')[0]
                    except:
                        pass
                
                web_info = await analyzer.get_company_info_from_web(company_name, gstin, location)
                
                if web_info.get('web_content'):
                    company_data['_web_content'] = web_info['web_content']
                    company_data['_web_summary'] = web_info['summary']
                    company_data['_web_keywords'] = web_info['keywords']
                
                synopsis = await analyzer.get_anthropic_synopsis(company_data)
                
                logger.info(f"Generated enhanced synopsis with web data: {synopsis[:100]}...")
                
            except Exception as e:
                logger.error(f"Failed to get enhanced AI synopsis: {e}")
                synopsis = await get_anthropic_synopsis(company_data)
        
        await db.add_search_history(current_user, gstin, company_data.get("lgnm", "Unknown"), compliance_score)
        
        late_filing_analysis = company_data.get('_late_filing_analysis', {})
        
        return templates.TemplateResponse("results.html", {
            "request": request, 
            "current_user": current_user, 
            "company_data": company_data,
            "compliance_score": int(compliance_score),
            "synopsis": synopsis,
            "late_filing_analysis": late_filing_analysis
        })
        
    except HTTPException as e:
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "current_user": current_user, 
            "error": e.detail, 
            "history": history
        })
    except Exception as e:
        logger.error(f"Search error: {e}")
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "current_user": current_user, 
            "error": "An error occurred while searching. Please try again.", 
            "history": history
        })

# =============================================================================
# LOAN ROUTES (COMPLETE INTEGRATION)
# =============================================================================

@app.get("/loans", response_class=HTMLResponse)
async def loans_page(request: Request, current_user: str = Depends(require_auth)):
    """Loans dashboard page"""
    try:
        applications = []
        if loan_manager:
            applications = await loan_manager.get_user_loan_applications(current_user)
        
        user_profile = await db.get_user_profile(current_user)
        user_display_name = await get_user_display_name(current_user)
        
        loan_config_data = {}
        if HAS_LOAN_MANAGEMENT and LoanConfig:
            loan_config_data = {
                "min_amount": LoanConfig.MIN_LOAN_AMOUNT,
                "max_amount": LoanConfig.MAX_LOAN_AMOUNT,
                "min_compliance": LoanConfig.MIN_COMPLIANCE_SCORE,
                "min_vintage": LoanConfig.MIN_BUSINESS_VINTAGE_MONTHS
            }
        
        return templates.TemplateResponse("loans.html", {
            "request": request,
            "current_user": current_user,
            "user_display_name": user_display_name,
            "user_profile": user_profile,
            "applications": applications,
            "loan_config": loan_config_data
        })
    except Exception as e:
        logger.error(f"Loans page error: {e}")
        return templates.TemplateResponse("loans.html", {
            "request": request,
            "current_user": current_user,
            "error": "Unable to load loans page"
        })

@app.post("/api/loans/apply")
@handle_api_errors
async def apply_for_loan(request: LoanApplicationRequest, current_user: str = Depends(require_auth)):
    """Apply for a business loan"""
    try:
        if not HAS_LOAN_MANAGEMENT or not loan_manager:
            return JSONResponse(
                status_code=503,
                content={"success": False, "error": "Loan service not available"}
            )
        
        application_data = request.dict()
        is_valid, message = LoanConfig.validate_loan_application(application_data)
        
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": message}
            )
        
        result = await loan_manager.submit_loan_application(current_user, application_data)
        
        if result["success"]:
            return {"success": True, "data": result, "message": "Loan application submitted successfully"}
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": result.get("error", "Application failed")}
            )
            
    except Exception as e:
        logger.error(f"Loan application error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to process loan application"}
        )

@app.get("/api/loans/applications")
@handle_api_errors
async def get_loan_applications(current_user: str = Depends(require_auth)):
    """Get user's loan applications"""
    try:
        if not HAS_LOAN_MANAGEMENT or not loan_manager:
            return {"success": True, "data": []}
        
        applications = await loan_manager.get_user_loan_applications(current_user)
        return {"success": True, "data": applications}
        
    except Exception as e:
        logger.error(f"Get loan applications error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to fetch loan applications"}
        )

@app.get("/api/loans/eligibility")
@handle_api_errors
async def check_loan_eligibility(
    gstin: str, 
    annual_turnover: float,
    compliance_score: float,
    business_vintage_months: int,
    current_user: str = Depends(require_auth)
):
    """Check loan eligibility for a business"""
    try:
        if not HAS_LOAN_MANAGEMENT or not LoanConfig:
            return JSONResponse(
                status_code=503,
                content={"success": False, "error": "Loan service not available"}
            )
        
        eligibility = {
            "eligible": True,
            "reasons": [],
            "max_loan_amount": 0,
            "recommended_amount": 0
        }
        
        if compliance_score < LoanConfig.MIN_COMPLIANCE_SCORE:
            eligibility["eligible"] = False
            eligibility["reasons"].append(f"Compliance score below minimum ({LoanConfig.MIN_COMPLIANCE_SCORE}%)")
        
        if business_vintage_months < LoanConfig.MIN_BUSINESS_VINTAGE_MONTHS:
            eligibility["eligible"] = False
            eligibility["reasons"].append(f"Business vintage below minimum ({LoanConfig.MIN_BUSINESS_VINTAGE_MONTHS} months)")
        
        if annual_turnover < LoanConfig.MIN_ANNUAL_TURNOVER:
            eligibility["eligible"] = False
            eligibility["reasons"].append(f"Annual turnover below minimum (₹{LoanConfig.MIN_ANNUAL_TURNOVER:,})")
        
        if eligibility["eligible"]:
            max_by_turnover = annual_turnover * LoanConfig.MAX_LOAN_TO_TURNOVER_RATIO
            eligibility["max_loan_amount"] = min(max_by_turnover, LoanConfig.MAX_LOAN_AMOUNT)
            
            score_multiplier = compliance_score / 100
            eligibility["recommended_amount"] = min(
                annual_turnover * 0.3 * score_multiplier,
                eligibility["max_loan_amount"]
            )
        
        return {"success": True, "data": eligibility}
        
    except Exception as e:
        logger.error(f"Eligibility check error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to check eligibility"}
        )

# =============================================================================
# OTHER ROUTES (Consolidated - continuing with other essential routes)
# =============================================================================

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, current_user: str = Depends(require_auth)):
    """Search history page."""
    history = await db.get_all_searches(current_user)
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)
    
    now = datetime.now()
    last_30_days = now - timedelta(days=30)
    searches_this_month = sum(
        1 for item in history
        if item.get('searched_at') and item['searched_at'] >= last_30_days
    )
    
    return templates.TemplateResponse("history.html", {
        "request": request, 
        "current_user": current_user,
        "user_display_name": user_display_name,
        "user_profile": user_profile,
        "history": history,
        "searches_this_month": searches_this_month
    })

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, current_user: str = Depends(require_auth)):
    """Analytics dashboard page."""
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)
    analytics_data = await db.get_analytics_data(current_user)
    
    stats = await db.get_user_stats(current_user)
    
    return templates.TemplateResponse("analytics.html", {
        "request": request, 
        "current_user": current_user,
        "user_display_name": user_display_name,
        "user_profile": user_profile,
        "daily_searches": analytics_data["daily_searches"],
        "score_distribution": analytics_data["score_distribution"],
        "top_companies": analytics_data["top_companies"],
        "total_searches": stats["total_searches"],
        "unique_companies": stats["unique_companies"],
        "avg_compliance": stats["avg_compliance"]
    })

# =============================================================================
# API ROUTES (Essential ones only)
# =============================================================================

@app.get("/api/user/stats")
@handle_api_errors
async def get_user_stats_api(current_user: str = Depends(require_auth)):
    """Get user statistics API."""
    stats = await db.get_user_stats(current_user)
    return {"success": True, "data": stats}

@app.post("/api/user/change-password")
@handle_api_errors
async def change_password_api(request: ChangePasswordRequest, current_user: str = Depends(require_auth)):
    """Change user password API."""
    success = await db.change_password(current_user, request.currentPassword, request.newPassword)
    
    if success:
        return {"success": True, "message": "Password changed successfully"}
    else:
        return {"success": False, "message": "Current password is incorrect"}

@app.get("/api/user/preferences")
@handle_api_errors
async def get_user_preferences_api(current_user: str = Depends(require_auth)):
    """Get user preferences API."""
    preferences = await db.get_user_preferences(current_user)
    return {"success": True, "data": preferences}

@app.post("/api/user/preferences")
@handle_api_errors
async def save_user_preferences_api(request: UserPreferencesRequest, current_user: str = Depends(require_auth)):
    """Save user preferences API."""
    preferences = request.dict()
    await db.save_user_preferences(current_user, preferences)
    return {"success": True, "message": "Preferences saved successfully"}

@app.get("/api/user/profile")
@handle_api_errors
async def get_user_profile_api(current_user: str = Depends(require_auth)):
    """Get user profile API."""
    profile = await db.get_user_profile(current_user)
    return {"success": True, "data": profile}

@app.post("/api/user/profile")
@handle_api_errors
async def save_user_profile_api(request: UserProfileRequest, current_user: str = Depends(require_auth)):
    """Save user profile API."""
    profile_data = {k: v for k, v in request.dict().items() if v is not None}
    await db.save_user_profile(current_user, profile_data)
    return {"success": True, "message": "Profile saved successfully"}

# =============================================================================
# ADMIN ROUTES (Fixed SQL injection)
# =============================================================================

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user: str = Depends(require_admin)):
    """Admin dashboard page."""
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)
    
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "current_user": current_user,
        "user_display_name": user_display_name,
        "user_profile": user_profile
    })

@app.post("/api/admin/bulk/delete-old-searches")
@handle_api_errors
async def bulk_delete_old_searches(
    days_old: int = 90,
    current_user: str = Depends(require_admin)
):
    """Delete search history older than specified days."""
    try:
        async with db.pool.acquire() as conn:
            result = await conn.fetchval("""
                WITH deleted AS (
                    DELETE FROM search_history 
                    WHERE searched_at < CURRENT_DATE - INTERVAL '1 day' * $1
                    RETURNING id
                )
                SELECT COUNT(*) FROM deleted
            """, days_old)
            
            return {
                'success': True,
                'deleted_count': result or 0,
                'days_old': days_old
            }
    except Exception as e:
        logger.error(f"Bulk delete error: {e}")
        return {'success': False, 'error': str(e)}

# =============================================================================
# STATIC FILES
# =============================================================================

@app.get("/favicon.ico")
async def favicon():
    """Favicon route."""
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

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
        return RedirectResponse(url=exc.headers["Location"], status_code=303)
    return JSONResponse(
        status_code=exc.status_code, 
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, 
        content={"error": "An internal error occurred"}
    )

# =============================================================================
# STARTUP/SHUTDOWN EVENTS
# =============================================================================

@app.on_event("startup")
async def startup():
    """Initialize application on startup."""
    logger.info("GST Intelligence Platform starting up...")
    await db.initialize()
    await db.cleanup_expired_sessions()
    
    if loan_manager:
        await loan_manager.initialize_loan_tables()
        logger.info("Loan management system initialized")
    
    app.extra = {"ADMIN_USERS": os.getenv("ADMIN_USERS", "")}
    
    logger.info("Application startup complete")
    
@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown."""
    logger.info("GST Intelligence Platform shutting down...")
    
    await cache_manager.close()
    
    if db.pool:
        await db.pool.close()
    
    logger.info("Cleanup complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)