#!/usr/bin/env python3
"""
Enhanced Database Manager for GST Intelligence Platform
Clean version - Database operations only (schema creation handled by complete_database_setup.py)
"""

import asyncio
import asyncpg
import logging
import time
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from contextlib import asynccontextmanager
from decimal import Decimal
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class DatabaseHealth:
    """Database health status."""
    is_connected: bool
    pool_size: int
    active_connections: int
    idle_connections: int
    redis_connected: bool
    last_check: datetime
    response_time_ms: float


class EnhancedDatabaseManager:
    """Enhanced database manager with proper connection pooling and error handling"""

    def __init__(self, postgres_dsn: str, redis_url: str = None):
        self.postgres_dsn = postgres_dsn
        self.redis_url = redis_url
        self.pool = None
        self.redis_client = None
        self._connection_retries = 3
        self._connection_retry_delay = 5
        self._cache = {}
        self._cache_ttl = {}
        self._initialized = False

    async def initialize(self):
        """Initialize database with proper error handling"""
        if self._initialized:
            return

        try:
            logger.info("🔧 Initializing database connections...")

            # PostgreSQL connection pool
            self.pool = await asyncpg.create_pool(
                dsn=self.postgres_dsn,
                min_size=2,
                max_size=20,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=30,
                server_settings={
                    'application_name': 'gst-intelligence-platform',
                    'timezone': 'UTC'
                })

            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")

            logger.info("✅ PostgreSQL pool created successfully")

            # Redis connection (optional)
            if self.redis_url:
                try:
                    import redis.asyncio as redis
                    self.redis_client = redis.from_url(
                        self.redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                        retry_on_timeout=True,
                        health_check_interval=30,
                        socket_connect_timeout=5,
                        socket_timeout=5)
                    await self.redis_client.ping()
                    logger.info("✅ Redis connected successfully")
                except Exception as e:
                    logger.warning(
                        f"⚠️ Redis connection failed, using memory cache: {e}")
                    self.redis_client = None

            # Verify all tables exist (they should be created by complete_database_setup.py)
            await self.verify_tables()

            self._initialized = True
            logger.info("✅ Database initialized successfully")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def verify_tables(self):
        """Verify that required tables exist (tables should be created by complete_database_setup.py)"""
        try:
            async with self.pool.acquire() as conn:
                # Check that essential tables exist
                required_tables = [
                    'users', 'user_profiles', 'user_sessions', 
                    'search_history', 'gst_search_history',
                    'loan_applications', 'loan_offers', 'active_loans',
                    'api_usage_logs', 'error_logs', 'system_metrics'
                ]
                
                for table in required_tables:
                    try:
                        await conn.fetchval(f"SELECT 1 FROM {table} LIMIT 1")
                    except Exception:
                        logger.error(f"❌ Required table '{table}' not found.")
                        logger.error("Please run 'python complete_database_setup.py' first to create the database schema.")
                        raise Exception(f"Database not properly initialized. Missing table: {table}")
                
                logger.info("✅ All required tables verified successfully")
                
        except Exception as e:
            logger.error(f"❌ Database table verification failed: {e}")
            raise

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection with automatic retry and health check"""
        if not self._initialized:
            await self.initialize()

        retries = 3
        for attempt in range(retries):
            try:
                async with self.pool.acquire() as conn:
                    # Quick health check
                    await conn.execute("SELECT 1")
                    yield conn
                    return

            except Exception as e:
                logger.error(
                    f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    raise ConnectionError("Database unavailable after retries")

    async def get_health_status(self) -> DatabaseHealth:
        """Get comprehensive database health status"""
        start_time = time.time()

        try:
            async with self.get_connection() as conn:
                await conn.execute("SELECT 1")

            pool_size = self.pool.get_size() if self.pool else 0
            active_connections = pool_size - self.pool.get_idle_size(
            ) if self.pool else 0
            idle_connections = self.pool.get_idle_size() if self.pool else 0

            # Test Redis connection
            redis_connected = False
            if self.redis_client:
                try:
                    await self.redis_client.ping()
                    redis_connected = True
                except:
                    pass

            response_time = (time.time() - start_time) * 1000

            return DatabaseHealth(is_connected=True,
                                  pool_size=pool_size,
                                  active_connections=active_connections,
                                  idle_connections=idle_connections,
                                  redis_connected=redis_connected,
                                  last_check=datetime.now(),
                                  response_time_ms=response_time)

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return DatabaseHealth(is_connected=False,
                                  pool_size=0,
                                  active_connections=0,
                                  idle_connections=0,
                                  redis_connected=False,
                                  last_check=datetime.now(),
                                  response_time_ms=0)

    # Cache operations
    async def cache_set(self, key: str, value: Any, ttl: int = 3600):
        """Set cache value with TTL"""
        if self.redis_client:
            try:
                serialized_value = json.dumps(value, default=str)
                await self.redis_client.setex(key, ttl, serialized_value)
                return True
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")

        # Fallback to memory cache
        self._cache[key] = value
        self._cache_ttl[key] = datetime.now() + timedelta(seconds=ttl)
        return True

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get cache value"""
        if self.redis_client:
            try:
                value = await self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis cache get failed: {e}")

        # Fallback to memory cache
        if key in self._cache:
            if datetime.now() < self._cache_ttl.get(key, datetime.min):
                return self._cache[key]
            else:
                # Expired
                del self._cache[key]
                if key in self._cache_ttl:
                    del self._cache_ttl[key]

        return None

    async def cache_delete(self, key: str):
        """Delete cache value"""
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis cache delete failed: {e}")

        # Memory cache
        if key in self._cache:
            del self._cache[key]
        if key in self._cache_ttl:
            del self._cache_ttl[key]

    # User management methods
    async def create_user(self,
                          mobile: str,
                          password_hash: str,
                          salt: str,
                          email: str = None,
                          **kwargs) -> bool:
        """Create new user with enhanced validation"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO users (mobile, password_hash, salt, email, profile_data)
                    VALUES ($1, $2, $3, $4, $5)
                """, mobile, password_hash, salt, email, json.dumps(kwargs))

                # Initialize user profile
                await conn.execute(
                    """
                    INSERT INTO user_profiles (mobile, display_name)
                    VALUES ($1, $2)
                """, mobile, f"User {mobile[-4:]}")

                # Log activity
                await self.log_user_activity(mobile, "USER_CREATED", {
                    "registration_method": "manual",
                    "has_email": bool(email)
                })

                logger.info(f"✅ User created successfully: {mobile}")
                return True

        except asyncpg.UniqueViolationError:
            logger.warning(f"⚠️ User already exists: {mobile}")
            return False
        except Exception as e:
            logger.error(f"❌ User creation failed: {e}")
            return False

    async def verify_user(self, mobile: str, password_hash: str) -> Optional[dict]:
        """Verify user credentials with security features"""
        try:
            async with self.get_connection() as conn:
                # Check if account is locked
                user = await conn.fetchrow(
                    """
                    SELECT mobile, password_hash, salt, is_active, is_verified,
                           failed_login_attempts, account_locked_until,
                           two_factor_enabled, profile_data
                    FROM users 
                    WHERE mobile = $1
                """, mobile)

                if not user:
                    await self.log_security_event(
                        mobile, "LOGIN_ATTEMPT_INVALID_USER")
                    return None

                # Check if account is locked
                if user['account_locked_until'] and user[
                        'account_locked_until'] > datetime.now():
                    await self.log_security_event(
                        mobile, "LOGIN_ATTEMPT_LOCKED_ACCOUNT")
                    return None

                # Check if active
                if not user['is_active']:
                    await self.log_security_event(
                        mobile, "LOGIN_ATTEMPT_INACTIVE_ACCOUNT")
                    return None

                # Verify password
                if user['password_hash'] == password_hash:
                    # Reset failed attempts on successful login
                    await conn.execute(
                        """
                        UPDATE users 
                        SET failed_login_attempts = 0, 
                            last_login_attempt = CURRENT_TIMESTAMP,
                            last_login = CURRENT_TIMESTAMP
                        WHERE mobile = $1
                    """, mobile)

                    await self.log_user_activity(mobile, "USER_LOGIN_SUCCESS")

                    return {
                        'mobile': user['mobile'],
                        'is_verified': user['is_verified'],
                        'two_factor_enabled': user['two_factor_enabled'],
                        'profile_data': user['profile_data']
                    }
                else:
                    # Increment failed attempts
                    failed_attempts = user['failed_login_attempts'] + 1

                    # Lock account after 5 failed attempts
                    lock_until = None
                    if failed_attempts >= 5:
                        lock_until = datetime.now() + timedelta(minutes=30)

                    await conn.execute(
                        """
                        UPDATE users 
                        SET failed_login_attempts = $1,
                            last_login_attempt = CURRENT_TIMESTAMP,
                            account_locked_until = $2
                        WHERE mobile = $3
                    """, failed_attempts, lock_until, mobile)

                    await self.log_security_event(
                        mobile, "LOGIN_ATTEMPT_INVALID_PASSWORD", {
                            "failed_attempts": failed_attempts,
                            "account_locked": bool(lock_until)
                        })

                    return None

        except Exception as e:
            logger.error(f"❌ User verification failed: {e}")
            return None

    async def verify_user_password(self, mobile: str, password: str) -> bool:
        """Verify user credentials (simplified version for compatibility)"""
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchrow(
                    "SELECT password_hash, salt FROM users WHERE mobile = $1 AND is_active = TRUE",
                    mobile
                )
                
                if result:
                    stored_hash = result["password_hash"]
                    salt = result["salt"]
                    
                    # Hash the provided password with the stored salt
                    password_hash = hashlib.pbkdf2_hmac(
                        'sha256', 
                        password.encode('utf-8'), 
                        salt.encode('utf-8'), 
                        100000, 
                        dklen=64
                    ).hex()
                    
                    return password_hash == stored_hash
                return False
        except Exception as e:
            logger.error(f"Error verifying user: {e}")
            return False

    # Session management
    async def create_session(self, mobile: str, ip_address: str = None, user_agent: str = None) -> str:
        """Create new user session"""
        try:
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=30)
            
            async with self.get_connection() as conn:
                await conn.execute(
                    """INSERT INTO user_sessions (session_id, user_mobile, expires_at, ip_address, user_agent) 
                       VALUES ($1, $2, $3, $4, $5)""",
                    session_id, mobile, expires_at, ip_address, user_agent
                )
                return session_id
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None

    async def get_session(self, session_token: str) -> Optional[str]:
        """Get user from session token"""
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchrow(
                    """SELECT user_mobile FROM user_sessions 
                       WHERE session_id = $1 AND expires_at > CURRENT_TIMESTAMP AND is_active = TRUE""",
                    session_token
                )
                
                if result:
                    # Update last activity
                    await conn.execute(
                        "UPDATE user_sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = $1",
                        session_token
                    )
                    return result["user_mobile"]
                return None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None

    async def delete_session(self, session_token: str) -> bool:
        """Delete user session"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    "UPDATE user_sessions SET is_active = FALSE WHERE session_id = $1",
                    session_token
                )
                return True
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False

    async def update_last_login(self, mobile: str) -> bool:
        """Update user's last login timestamp"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE mobile = $1",
                    mobile
                )
                return True
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False

    # Search history management
    async def add_search_history(self, mobile: str, gstin: str, company_name: str, compliance_score: float, search_data: dict = None, ai_synopsis: str = None) -> bool:
        """Add search to history"""
        try:
            async with self.get_connection() as conn:
                # Add to both tables for compatibility
                await conn.execute(
                    """INSERT INTO search_history 
                       (mobile, gstin, company_name, compliance_score, search_data, ai_synopsis) 
                       VALUES ($1, $2, $3, $4, $5, $6)""",
                    mobile, gstin, company_name, compliance_score, json.dumps(search_data or {}), ai_synopsis
                )
                
                await conn.execute(
                    """INSERT INTO gst_search_history 
                       (user_mobile, mobile, gstin, company_name, compliance_score, search_data, ai_synopsis, response_data) 
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                    mobile, mobile, gstin, company_name, compliance_score, 
                    json.dumps(search_data or {}), ai_synopsis, json.dumps(search_data or {})
                )
                return True
        except Exception as e:
            logger.error(f"Error adding search history: {e}")
            return False

    async def get_search_history(self, mobile: str, limit: int = 50) -> List[Dict]:
        """Get user search history"""
        try:
            async with self.get_connection() as conn:
                history = await conn.fetch(
                    """SELECT gstin, company_name, compliance_score, ai_synopsis, searched_at 
                       FROM search_history 
                       WHERE mobile = $1 
                       ORDER BY searched_at DESC 
                       LIMIT $2""", 
                    mobile, limit
                )
                return [dict(row) for row in history]
        except Exception as e:
            logger.error(f"Error getting search history: {e}")
            return []

    async def get_all_searches(self, mobile: str) -> List[Dict]:
        """Get all searches for user"""
        try:
            async with self.get_connection() as conn:
                history = await conn.fetch(
                    """SELECT gstin, company_name, compliance_score, searched_at 
                       FROM search_history 
                       WHERE mobile = $1 
                       ORDER BY searched_at DESC""", 
                    mobile
                )
                return [dict(row) for row in history]
        except Exception as e:
            logger.error(f"Error getting all searches: {e}")
            return []

    # User statistics and analytics
    async def get_user_stats(self, mobile: str) -> Dict[str, Any]:
        """Get user statistics for dashboard"""
        try:
            async with self.get_connection() as conn:
                # Get search count
                search_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM search_history WHERE mobile = $1", mobile
                )

                # Get average compliance score
                avg_compliance = await conn.fetchval(
                    "SELECT AVG(compliance_score) FROM search_history WHERE mobile = $1", mobile
                )

                # Get unique companies searched
                unique_companies = await conn.fetchval(
                    "SELECT COUNT(DISTINCT gstin) FROM search_history WHERE mobile = $1", mobile
                )

                # Get recent searches (last 30 days)
                searches_this_month = await conn.fetchval(
                    """SELECT COUNT(*) FROM search_history 
                       WHERE mobile = $1 AND searched_at >= DATE_TRUNC('month', CURRENT_DATE)""", 
                    mobile
                )

                return {
                    "total_searches": search_count or 0,
                    "avg_compliance": round(float(avg_compliance or 0), 1),
                    "unique_companies": unique_companies or 0,
                    "searches_this_month": searches_this_month or 0
                }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"total_searches": 0, "avg_compliance": 0, "unique_companies": 0, "searches_this_month": 0}

    async def get_user_profile_data(self, mobile: str) -> Dict[str, Any]:
        """Get user profile data"""
        try:
            async with self.get_connection() as conn:
                user_data = await conn.fetchrow(
                    "SELECT mobile, email, created_at, last_login, profile_data FROM users WHERE mobile = $1", 
                    mobile
                )
                
                search_stats = await self.get_user_stats(mobile)
                recent_searches = await self.get_search_history(mobile, 5)
                
                return {
                    "user_info": dict(user_data) if user_data else {},
                    "search_stats": search_stats,
                    "recent_searches": recent_searches
                }
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return {"user_info": {}, "search_stats": {}, "recent_searches": []}

    # Logging methods
    async def log_user_activity(self,
                                mobile: str,
                                activity_type: str,
                                activity_data: dict = None,
                                ip_address: str = None,
                                user_agent: str = None,
                                session_id: str = None):
        """Log user activity"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO user_activity_logs 
                    (user_mobile, activity_type, activity_data, ip_address, user_agent, session_id)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, mobile, activity_type, json.dumps(activity_data or {}),
                    ip_address, user_agent, session_id)
        except Exception as e:
            logger.error(f"Failed to log user activity: {e}")

    async def log_security_event(self,
                                 mobile: str,
                                 event_type: str,
                                 event_data: dict = None):
        """Log security events"""
        try:
            await self.log_user_activity(mobile, f"SECURITY_{event_type}",
                                         event_data)
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    async def log_error(self,
                        error_type: str,
                        message: str,
                        stack_trace: str = None,
                        user_mobile: str = None,
                        additional_data: dict = None,
                        severity: str = "ERROR",
                        url: str = None,
                        method: str = None):
        """Log application errors"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO error_logs 
                    (error_type, message, stack_trace, user_mobile, additional_data, severity, url, method)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, error_type, message, stack_trace, user_mobile,
                    json.dumps(additional_data or {}), severity, url, method)
        except Exception as e:
            logger.error(f"Failed to log error: {e}")

    async def log_api_usage(self,
                           user_mobile: str,
                           endpoint: str,
                           method: str,
                           response_status: int,
                           response_time_ms: int,
                           ip_address: str = None,
                           user_agent: str = None,
                           request_params: dict = None):
        """Log API usage"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO api_usage_logs 
                    (user_mobile, endpoint, method, response_status, response_time_ms, 
                     ip_address, user_agent, request_params)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, user_mobile, endpoint, method, response_status, response_time_ms,
                    ip_address, user_agent, json.dumps(request_params or {}))
        except Exception as e:
            logger.error(f"Failed to log API usage: {e}")

    # System maintenance
    async def cleanup_expired_data(self):
        """Clean up expired data from database"""
        try:
            async with self.get_connection() as conn:
                # Clean expired sessions
                deleted_sessions = await conn.fetchval("""
                    DELETE FROM user_sessions 
                    WHERE expires_at < CURRENT_TIMESTAMP
                    RETURNING COUNT(*)
                """)

                # Clean old error logs (keep 30 days for resolved, 90 days for unresolved)
                deleted_errors = await conn.fetchval("""
                    DELETE FROM error_logs 
                    WHERE (resolved = TRUE AND created_at < CURRENT_TIMESTAMP - INTERVAL '30 days')
                       OR (resolved = FALSE AND created_at < CURRENT_TIMESTAMP - INTERVAL '90 days')
                    RETURNING COUNT(*)
                """)

                # Clean old activity logs (keep 90 days)
                deleted_activities = await conn.fetchval("""
                    DELETE FROM user_activity_logs 
                    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
                    RETURNING COUNT(*)
                """)

                # Clean expired file uploads
                deleted_files = await conn.fetchval("""
                    DELETE FROM file_uploads 
                    WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
                    RETURNING COUNT(*)
                """)

                # Clean processed notifications (keep 7 days)
                deleted_notifications = await conn.fetchval("""
                    DELETE FROM notification_queue 
                    WHERE status = 'sent' 
                    AND sent_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
                    RETURNING COUNT(*)
                """)

                logger.info(f"✅ Database cleanup completed: {deleted_sessions} sessions, "
                          f"{deleted_errors} errors, {deleted_activities} activities, "
                          f"{deleted_files} files, {deleted_notifications} notifications")

        except Exception as e:
            logger.error(f"❌ Database cleanup failed: {e}")

    # Loan-related methods (basic support)
    async def get_user_loan_applications(self, mobile: str) -> List[Dict]:
        """Get user's loan applications"""
        try:
            async with self.get_connection() as conn:
                applications = await conn.fetch(
                    """SELECT * FROM loan_applications 
                       WHERE user_mobile = $1 
                       ORDER BY created_at DESC""",
                    mobile
                )
                return [dict(row) for row in applications]
        except Exception as e:
            logger.error(f"Error getting loan applications: {e}")
            return []

    async def get_user_active_loans(self, mobile: str) -> List[Dict]:
        """Get user's active loans"""
        try:
            async with self.get_connection() as conn:
                loans = await conn.fetch(
                    """SELECT al.*, la.company_name, la.gstin 
                       FROM active_loans al
                       JOIN loan_applications la ON al.application_id = la.application_id
                       WHERE al.user_mobile = $1 AND al.status = 'active'
                       ORDER BY al.created_at DESC""",
                    mobile
                )
                return [dict(row) for row in loans]
        except Exception as e:
            logger.error(f"Error getting active loans: {e}")
            return []

    async def close(self):
        """Close database connections"""
        try:
            if self.redis_client:
                await self.redis_client.close()

            if self.pool:
                await self.pool.close()

            self._initialized = False
            logger.info("✅ Database connections closed")

        except Exception as e:
            logger.error(f"❌ Error closing database connections: {e}")

    # Compatibility methods (for existing code)
    async def connect(self):
        """Compatibility method - calls initialize()"""
        await self.initialize()

    async def verify_user(self, mobile: str, password: str) -> bool:
        """Verify user credentials (simple version for compatibility)"""
        return await self.verify_user_password(mobile, password)


# Global database instance
db_manager = None


async def get_database() -> EnhancedDatabaseManager:
    """Get global database manager instance"""
    global db_manager
    if db_manager is None:
        from config import settings
        db_manager = EnhancedDatabaseManager(
            postgres_dsn=settings.POSTGRES_DSN,
            redis_url=getattr(settings, 'REDIS_URL', None))
        await db_manager.initialize()
    return db_manager


# Example usage and testing
if __name__ == "__main__":

    async def test_database():
        """Test database functionality"""
        try:
            # Initialize database
            db = EnhancedDatabaseManager(
                postgres_dsn="postgresql://user:pass@localhost:5432/test_db")
            await db.initialize()

            # Test health check
            health = await db.get_health_status()
            print(f"Database Health: {asdict(health)}")

            # Test user creation
            success = await db.create_user(
                mobile="9876543210",
                password_hash=hashlib.sha256(b"password123").hexdigest(),
                salt=secrets.token_hex(16),
                email="test@example.com")
            print(f"User creation: {'✅' if success else '❌'}")

            # Test caching
            await db.cache_set("test_key", {"data": "value"}, ttl=300)
            cached_value = await db.cache_get("test_key")
            print(f"Cache test: {'✅' if cached_value else '❌'}")

            # Clean up
            await db.close()
            print("✅ Database test completed successfully")

        except Exception as e:
            print(f"❌ Database test failed: {e}")

    # Run test
    asyncio.run(test_database())