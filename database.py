#!/usr/bin/env python3
"""
Complete Database Manager for GST Intelligence Platform
Production-ready with connection pooling, retry logic, and comprehensive error handling
"""

import asyncio
import asyncpg
import logging
import hashlib
import secrets
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any, Tuple
import time

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Production-ready database manager with connection pooling and error handling."""
    
    def __init__(self, dsn: str = None):
        try:
            from config import settings
            self.dsn = dsn or settings.POSTGRES_DSN
        except ImportError:
            import os
            self.dsn = dsn or os.getenv("POSTGRES_DSN")
            
        if not self.dsn:
            raise ValueError("Database DSN is required")
            
        self.pool = None
        self.is_initialized = False
        self.retry_attempts = 3
        self.retry_delay = 2
        
        # Simple in-memory cache with TTL
        self._cache = {}
        self._cache_ttl = {}
        self._cache_max_size = 1000
        
    async def initialize(self):
        """Initialize database connection pool with retry logic."""
        if self.is_initialized:
            return True
            
        for attempt in range(self.retry_attempts):
            try:
                self.pool = await asyncpg.create_pool(
                    dsn=self.dsn,
                    min_size=2,
                    max_size=20,
                    timeout=30,
                    command_timeout=30,
                    server_settings={
                        'jit': 'off',  # Disable JIT for faster startup
                        'application_name': 'gst_intelligence'
                    }
                )
                
                # Test connection
                async with self.pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                
                logger.info("✅ Database initialized successfully")
                self.is_initialized = True
                return True
                
            except Exception as e:
                logger.error(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error("❌ Database initialization failed after all attempts")
                    raise
    
    async def close(self):
        """Close database pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self.is_initialized = False
            logger.info("Database pool closed")
    
    def _cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        return ":".join(str(arg) for arg in args)
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            if time.time() < self._cache_ttl.get(key, 0):
                return self._cache[key]
            else:
                # Cleanup expired entry
                self._cache.pop(key, None)
                self._cache_ttl.pop(key, None)
        return None
    
    def _set_cache(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set cache value with TTL."""
        # Limit cache size
        if len(self._cache) >= self._cache_max_size:
            # Remove oldest entries
            current_time = time.time()
            expired_keys = [k for k, expire_time in self._cache_ttl.items() if current_time >= expire_time]
            for k in expired_keys:
                self._cache.pop(k, None)
                self._cache_ttl.pop(k, None)
            
            # If still too large, remove half randomly
            if len(self._cache) >= self._cache_max_size:
                keys_to_remove = list(self._cache.keys())[:self._cache_max_size // 2]
                for k in keys_to_remove:
                    self._cache.pop(k, None)
                    self._cache_ttl.pop(k, None)
        
        self._cache[key] = value
        self._cache_ttl[key] = time.time() + ttl_seconds
    
    # =============================================
    # USER MANAGEMENT
    # =============================================
    
    async def create_user(self, mobile: str, password_hash: str, salt: str) -> bool:
        """Create new user."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (mobile, password_hash, salt, created_at)
                    VALUES ($1, $2, $3, $4)
                """, mobile, password_hash, salt, datetime.now())
                return True
        except asyncpg.UniqueViolationError:
            return False
        except Exception as e:
            logger.error(f"Create user error: {e}")
            return False
    
    async def verify_user(self, mobile: str, password: str) -> bool:
        """Verify user credentials."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT password_hash, salt FROM users WHERE mobile = $1
                """, mobile)
                
                if not row:
                    return False
                
                # Verify password
                password_hash = hashlib.pbkdf2_hmac(
                    'sha256', password.encode('utf-8'),
                    row['salt'].encode('utf-8'), 100000, dklen=64
                ).hex()
                
                is_valid = password_hash == row['password_hash']
                
                if is_valid:
                    # Update last login with timezone-aware datetime
                    await conn.execute("""
                        UPDATE users SET last_login = $1 WHERE mobile = $2
                    """, datetime.now(), mobile)
                
                    return is_valid
                
        except Exception as e:
            logger.error(f"Verify user error: {e}")
            return False
    
    async def user_exists(self, mobile: str) -> bool:
        """Check if user exists."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("""
                    SELECT EXISTS(SELECT 1 FROM users WHERE mobile = $1)
                """, mobile)
                return result
        except Exception as e:
            logger.error(f"User exists check error: {e}")
            return False
    
    async def change_password(self, mobile: str, current_password: str, new_password: str) -> bool:
        """Change user password."""
        # First verify current password
        if not await self.verify_user(mobile, current_password):
            return False
        
        try:
            # Generate new salt and hash
            salt = secrets.token_hex(16)
            password_hash = hashlib.pbkdf2_hmac(
                'sha256', new_password.encode('utf-8'),
                salt.encode('utf-8'), 100000, dklen=64
            ).hex()
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE users SET password_hash = $1, salt = $2, updated_at = $3
                    WHERE mobile = $4
                """, password_hash, salt, datetime.now(), mobile)
            
            return True
        except Exception as e:
            logger.error(f"Change password error: {e}")
            return False
    
    # =============================================
    # SESSION MANAGEMENT
    # =============================================
    
    async def create_session(self, mobile: str, expires_at: datetime) -> str:
        """Create a new user session."""
        import secrets
        session_token = secrets.token_urlsafe(32)
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO sessions (session_token, mobile, expires_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (session_token) DO UPDATE SET
                    mobile = EXCLUDED.mobile,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = CURRENT_TIMESTAMP
            """, session_token, mobile, expires_at)
        
        logger.info(f"✅ Session created for {mobile}")
        return session_token

    async def get_session(self, session_token: str) -> Optional[str]:
        """Get user mobile from session token."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT mobile, expires_at 
                FROM sessions 
                WHERE session_token = $1 AND expires_at > NOW()
            """, session_token)
        
        if result:
            return result["mobile"]
        return None

    async def delete_session(self, session_token: str) -> bool:
        """Delete a user session."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM sessions WHERE session_token = $1
            """, session_token)
        
        return result != "DELETE 0"

    async def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM sessions WHERE expires_at <= NOW()
                """)
                count = int(result.split()[-1]) if result.split() else 0
                if count > 0:
                    logger.info(f"🧹 Cleaned up {count} expired sessions")
        except Exception as e:
            logger.error(f"Cleanup sessions error: {e}")

    async def get_all_sessions(self, mobile: str) -> List[dict]:
        """Get all sessions for a user."""
        async with self.pool.acquire() as conn:
            result = await conn.fetch("""
                SELECT session_token, expires_at, created_at
                FROM sessions 
                WHERE mobile = $1 AND expires_at > NOW()
                ORDER BY created_at DESC
            """, mobile)
        
        return [dict(row) for row in result]

    async def delete_all_user_sessions(self, mobile: str) -> int:
        """Delete all sessions for a user."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM sessions WHERE mobile = $1
            """, mobile)
        
        count = int(result.split()[-1]) if result.split() else 0
        logger.info(f"🧹 Deleted {count} sessions for {mobile}")
        return count
    
    # =============================================
    # SEARCH HISTORY
    # =============================================
    
    async def save_search(self, mobile: str, gstin: str, company_data: Dict[str, Any] = None) -> bool:
        """Save search to history."""
        try:
            company_name = None
            compliance_score = None
            status = None
            
            if company_data:
                company_name = company_data.get('company_name') or company_data.get('tradeNam')
                compliance_score = company_data.get('compliance_score')
                status = company_data.get('status') or company_data.get('sts')
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO search_history 
                    (mobile, gstin, company_name, compliance_score, status, search_data, searched_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (mobile, gstin) 
                    DO UPDATE SET 
                        company_name = EXCLUDED.company_name,
                        compliance_score = EXCLUDED.compliance_score,
                        status = EXCLUDED.status,
                        search_data = EXCLUDED.search_data,
                        searched_at = EXCLUDED.searched_at,
                        search_count = search_history.search_count + 1
                """, mobile, gstin, company_name, compliance_score, status, 
                json.dumps(company_data) if company_data else None, 
                datetime.now())
            
            return True
        except Exception as e:
            logger.error(f"Save search error: {e}")
            return False
    
    async def get_search_history(self, mobile: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's search history."""
        cache_key = self._cache_key("history", mobile, limit, offset)
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT gstin, company_name, compliance_score, status, 
                           search_count, searched_at, search_data
                    FROM search_history 
                    WHERE mobile = $1 
                    ORDER BY searched_at DESC 
                    LIMIT $2 OFFSET $3
                """, mobile, limit, offset)
                
                history = []
                for row in rows:
                    item = dict(row)
                    if item['search_data']:
                        try:
                            item['search_data'] = json.loads(item['search_data'])
                        except:
                            item['search_data'] = {}
                    history.append(item)
                
                self._set_cache(cache_key, history, 120)  # Cache for 2 minutes
                return history
                
        except Exception as e:
            logger.error(f"Get search history error: {e}")
            return []
    
    async def get_all_searches(self, mobile: str) -> List[Dict[str, Any]]:
        """Get all user searches (for export)."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT gstin, company_name, compliance_score, status, 
                           search_count, searched_at, search_data
                    FROM search_history 
                    WHERE mobile = $1 
                    ORDER BY searched_at DESC
                """, mobile)
                
                history = []
                for row in rows:
                    item = dict(row)
                    if item['search_data']:
                        try:
                            item['search_data'] = json.loads(item['search_data'])
                        except:
                            item['search_data'] = {}
                    history.append(item)
                
                return history
                
        except Exception as e:
            logger.error(f"Get all searches error: {e}")
            return []
    
    async def delete_search(self, mobile: str, gstin: str) -> bool:
        """Delete specific search from history."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("""
                    DELETE FROM search_history 
                    WHERE mobile = $1 AND gstin = $2
                    RETURNING id
                """, mobile, gstin)
                
                return result is not None
        except Exception as e:
            logger.error(f"Delete search error: {e}")
            return False
    
    async def clear_search_history(self, mobile: str) -> bool:
        """Clear all search history for user."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM search_history WHERE mobile = $1", mobile)
            return True
        except Exception as e:
            logger.error(f"Clear search history error: {e}")
            return False
    
    # =============================================
    # USER PREFERENCES & PROFILE
    # =============================================
    
    async def get_user_preferences(self, mobile: str) -> Dict[str, Any]:
        """Get user preferences."""
        cache_key = self._cache_key("prefs", mobile)
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT preferences FROM user_preferences WHERE mobile = $1
                """, mobile)
                
                if row and row['preferences']:
                    prefs = json.loads(row['preferences'])
                else:
                    prefs = {
                        'theme': 'dark',
                        'notifications': True,
                        'analytics': True,
                        'auto_save': True,
                        'email_reports': False
                    }
                
                self._set_cache(cache_key, prefs, 600)  # Cache for 10 minutes
                return prefs
                
        except Exception as e:
            logger.error(f"Get user preferences error: {e}")
            return {}
    
    async def save_user_preferences(self, mobile: str, preferences: Dict[str, Any]) -> bool:
        """Save user preferences."""
        try:
            # Clear cache
            cache_key = self._cache_key("prefs", mobile)
            self._cache.pop(cache_key, None)
            self._cache_ttl.pop(cache_key, None)
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_preferences (mobile, preferences, updated_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (mobile) 
                    DO UPDATE SET 
                        preferences = EXCLUDED.preferences,
                        updated_at = EXCLUDED.updated_at
                """, mobile, json.dumps(preferences), datetime.now())
            
            return True
        except Exception as e:
            logger.error(f"Save user preferences error: {e}")
            return False
    
    async def get_user_profile(self, mobile: str) -> Dict[str, Any]:
        """Get user profile."""
        cache_key = self._cache_key("profile", mobile)
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT display_name, company, email, designation 
                    FROM user_profiles WHERE mobile = $1
                """, mobile)
                
                if row:
                    profile = dict(row)
                else:
                    profile = {
                        'display_name': None,
                        'company': None,
                        'email': None,
                        'designation': None
                    }
                
                self._set_cache(cache_key, profile, 600)  # Cache for 10 minutes
                return profile
                
        except Exception as e:
            logger.error(f"Get user profile error: {e}")
            return {}
    
    async def save_user_profile(self, mobile: str, profile_data: Dict[str, Any]) -> bool:
        """Save user profile."""
        try:
            # Clear cache
            cache_key = self._cache_key("profile", mobile)
            self._cache.pop(cache_key, None)
            self._cache_ttl.pop(cache_key, None)
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_profiles 
                    (mobile, display_name, company, email, designation, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (mobile) 
                    DO UPDATE SET 
                        display_name = EXCLUDED.display_name,
                        company = EXCLUDED.company,
                        email = EXCLUDED.email,
                        designation = EXCLUDED.designation,
                        updated_at = EXCLUDED.updated_at
                """, mobile, 
                profile_data.get('display_name'),
                profile_data.get('company'),
                profile_data.get('email'),
                profile_data.get('designation'),
                datetime.now())
            
            return True
        except Exception as e:
            logger.error(f"Save user profile error: {e}")
            return False
    
    # =============================================
    # ANALYTICS & STATS
    # =============================================
    
    async def get_user_stats(self, mobile: str) -> Dict[str, Any]:
        """Get user statistics."""
        cache_key = self._cache_key("stats", mobile)
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        try:
            async with self.pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_searches,
                        COUNT(DISTINCT gstin) as unique_companies,
                        AVG(compliance_score) as avg_compliance,
                        MAX(searched_at) as last_search
                    FROM search_history 
                    WHERE mobile = $1
                """, mobile)
                
                if stats:
                    result = {
                        'total_searches': stats['total_searches'] or 0,
                        'unique_companies': stats['unique_companies'] or 0,
                        'avg_compliance': round(stats['avg_compliance'] or 0, 1),
                        'last_search': stats['last_search']
                    }
                else:
                    result = {
                        'total_searches': 0,
                        'unique_companies': 0,
                        'avg_compliance': 0,
                        'last_search': None
                    }
                
                self._set_cache(cache_key, result, 300)  # Cache for 5 minutes
                return result
                
        except Exception as e:
            logger.error(f"Get user stats error: {e}")
            return {
                'total_searches': 0,
                'unique_companies': 0,
                'avg_compliance': 0,
                'last_search': None
            }
    
    async def get_analytics_data(self, mobile: str) -> Dict[str, Any]:
        """Get analytics data for charts."""
        try:
            async with self.pool.acquire() as conn:
                # Daily search counts (last 30 days)
                daily_searches = await conn.fetch("""
                    SELECT 
                        DATE(searched_at) as search_date,
                        COUNT(*) as search_count
                    FROM search_history 
                    WHERE mobile = $1 
                      AND searched_at >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY DATE(searched_at)
                    ORDER BY search_date
                """, mobile)
                
                # Compliance score distribution
                score_distribution = await conn.fetch("""
                    SELECT 
                        CASE 
                            WHEN compliance_score >= 80 THEN 'High (80-100)'
                            WHEN compliance_score >= 50 THEN 'Medium (50-79)'
                            WHEN compliance_score >= 20 THEN 'Low (20-49)'
                            ELSE 'Very Low (0-19)'
                        END as score_range,
                        COUNT(*) as count
                    FROM search_history 
                    WHERE mobile = $1 AND compliance_score IS NOT NULL
                    GROUP BY score_range
                    ORDER BY score_range
                """, mobile)
                
                # Top companies by search frequency
                top_companies = await conn.fetch("""
                    SELECT company_name, search_count, compliance_score
                    FROM search_history 
                    WHERE mobile = $1 AND company_name IS NOT NULL
                    ORDER BY search_count DESC, searched_at DESC
                    LIMIT 10
                """, mobile)
                
                return {
                    'daily_searches': [dict(row) for row in daily_searches],
                    'score_distribution': [dict(row) for row in score_distribution],
                    'top_companies': [dict(row) for row in top_companies]
                }
                
        except Exception as e:
            logger.error(f"Get analytics data error: {e}")
            return {
                'daily_searches': [],
                'score_distribution': [],
                'top_companies': []
            }
    
    # =============================================
    # ADMIN FUNCTIONS
    # =============================================
    
    async def get_all_users(self, page: int = 1, per_page: int = 50, search: str = None) -> Dict[str, Any]:
        """Get paginated list of all users (admin only)."""
        try:
            offset = (page - 1) * per_page
            search_pattern = f"%{search}%" if search else "%"
            
            async with self.pool.acquire() as conn:
                # Get total count
                total = await conn.fetchval("""
                    SELECT COUNT(*) FROM users WHERE mobile LIKE $1
                """, search_pattern)
                
                # Get users
                users = await conn.fetch("""
                    SELECT mobile, created_at, last_login,
                           (SELECT COUNT(*) FROM search_history WHERE mobile = users.mobile) as search_count
                    FROM users 
                    WHERE mobile LIKE $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                """, search_pattern, per_page, offset)
                
                return {
                    'users': [dict(user) for user in users],
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total + per_page - 1) // per_page
                }
        except Exception as e:
            logger.error(f"Get users list error: {e}")
            return {'users': [], 'total': 0, 'page': 1, 'per_page': per_page, 'total_pages': 0}
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide statistics (admin only)."""
        try:
            async with self.pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        (SELECT COUNT(*) FROM users) as total_users,
                        (SELECT COUNT(*) FROM search_history) as total_searches,
                        (SELECT COUNT(DISTINCT gstin) FROM search_history) as unique_companies,
                        (SELECT COUNT(*) FROM sessions WHERE expires_at > NOW()) as active_sessions
                """)
                
                return dict(stats) if stats else {}
        except Exception as e:
            logger.error(f"Get system stats error: {e}")
            return {}
    
    # =============================================
    # ERROR LOGGING
    # =============================================
    
    async def log_error(self, error_data: Dict[str, Any]) -> bool:
        """Log application error to database."""
        try:
            async with self.pool.acquire() as conn:
                # First check if mobile column exists
                mobile_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'error_logs' AND column_name = 'mobile'
                    );
                """)
                
                # Use timezone-aware datetime
                current_time = datetime.now()
                
                if mobile_exists:
                    # Use the full insert with mobile column
                    await conn.execute("""
                        INSERT INTO error_logs 
                        (error_type, message, stack_trace, url, user_agent, mobile, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, 
                    error_data.get('type'),
                    error_data.get('message'),
                    error_data.get('stack'),
                    error_data.get('url'),
                    error_data.get('userAgent'),
                    error_data.get('mobile'),
                    current_time)
                else:
                    # Use insert without mobile column
                    await conn.execute("""
                        INSERT INTO error_logs 
                        (error_type, message, stack_trace, url, user_agent, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, 
                    error_data.get('type'),
                    error_data.get('message'),
                    error_data.get('stack'),
                    error_data.get('url'),
                    error_data.get('userAgent'),
                    current_time)
            
            return True
        except Exception as e:
            logger.error(f"Log error failed: {e}")
            return False