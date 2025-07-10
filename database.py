#!/usr/bin/env python3
"""
Enhanced Database Manager with Connection Pooling and Error Handling
Complete implementation for GST Intelligence Platform
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

            # Ensure all tables exist
            await self.ensure_tables()

            self._initialized = True
            logger.info("✅ Database initialized successfully")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def ensure_tables(self):
        """Create all required tables with proper indexes and constraints"""
        async with self.pool.acquire() as conn:

            # Start transaction for schema creation
            async with conn.transaction():

                # Users table with enhanced security
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        mobile VARCHAR(15) PRIMARY KEY CHECK (mobile ~ '^[+]?[0-9]{10,15}$'),
                        password_hash VARCHAR(255) NOT NULL,
                        salt VARCHAR(64) NOT NULL,
                        email VARCHAR(255) UNIQUE,
                        is_active BOOLEAN DEFAULT TRUE,
                        is_verified BOOLEAN DEFAULT FALSE,
                        failed_login_attempts INTEGER DEFAULT 0,
                        last_login_attempt TIMESTAMP,
                        account_locked_until TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_password_change TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        two_factor_enabled BOOLEAN DEFAULT FALSE,
                        two_factor_secret VARCHAR(32),
                        backup_codes TEXT[],
                        profile_data JSONB DEFAULT '{}',
                        preferences JSONB DEFAULT '{}',
                        metadata JSONB DEFAULT '{}'
                    );
                """)

                # User profiles table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        mobile VARCHAR(15) PRIMARY KEY REFERENCES users(mobile) ON DELETE CASCADE,
                        display_name VARCHAR(255),
                        full_name VARCHAR(255),
                        company_name VARCHAR(500),
                        gstin VARCHAR(15),
                        pan VARCHAR(10),
                        business_type VARCHAR(100),
                        annual_turnover DECIMAL(15,2),
                        business_address TEXT,
                        city VARCHAR(100),
                        state VARCHAR(100),
                        pincode VARCHAR(10),
                        website VARCHAR(500),
                        industry_type VARCHAR(100),
                        employee_count INTEGER,
                        registration_date DATE,
                        compliance_score INTEGER DEFAULT 0,
                        risk_category VARCHAR(20) DEFAULT 'UNKNOWN',
                        kyc_status VARCHAR(20) DEFAULT 'PENDING',
                        profile_completion_percent INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # GST search history with enhanced tracking
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS gst_search_history (
                        id SERIAL PRIMARY KEY,
                        user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                        gstin VARCHAR(15) NOT NULL,
                        search_type VARCHAR(50) DEFAULT 'basic',
                        search_params JSONB DEFAULT '{}',
                        response_data JSONB,
                        response_time_ms INTEGER,
                        api_source VARCHAR(100),
                        success BOOLEAN DEFAULT TRUE,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ip_address INET,
                        user_agent TEXT,
                        session_id VARCHAR(128)
                    );
                """)

                # Enhanced sessions table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id VARCHAR(128) PRIMARY KEY,
                        user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                        session_data JSONB DEFAULT '{}',
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ip_address INET,
                        user_agent TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        device_fingerprint VARCHAR(128),
                        location_data JSONB
                    );
                """)

                # API usage tracking
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_usage_logs (
                        id SERIAL PRIMARY KEY,
                        user_mobile VARCHAR(15) REFERENCES users(mobile) ON DELETE SET NULL,
                        endpoint VARCHAR(255) NOT NULL,
                        method VARCHAR(10) NOT NULL,
                        request_params JSONB,
                        response_status INTEGER,
                        response_time_ms INTEGER,
                        api_key_used VARCHAR(50),
                        rate_limited BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ip_address INET,
                        user_agent TEXT,
                        request_size_bytes INTEGER,
                        response_size_bytes INTEGER
                    );
                """)

                # Error logging table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS error_logs (
                        id SERIAL PRIMARY KEY,
                        error_type VARCHAR(100) NOT NULL,
                        error_code VARCHAR(50),
                        message TEXT NOT NULL,
                        stack_trace TEXT,
                        url TEXT,
                        method VARCHAR(10),
                        user_mobile VARCHAR(15) REFERENCES users(mobile) ON DELETE SET NULL,
                        session_id VARCHAR(128),
                        request_data JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        resolved BOOLEAN DEFAULT FALSE,
                        resolution_notes TEXT,
                        severity VARCHAR(20) DEFAULT 'ERROR',
                        environment VARCHAR(20),
                        version VARCHAR(20),
                        additional_data JSONB
                    );
                """)

                # System health metrics
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id SERIAL PRIMARY KEY,
                        metric_name VARCHAR(100) NOT NULL,
                        metric_value DECIMAL(15,4),
                        metric_unit VARCHAR(20),
                        tags JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # User activity logs
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_activity_logs (
                        id SERIAL PRIMARY KEY,
                        user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                        activity_type VARCHAR(100) NOT NULL,
                        activity_data JSONB DEFAULT '{}',
                        ip_address INET,
                        user_agent TEXT,
                        session_id VARCHAR(128),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # Notification queue
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS notification_queue (
                        id SERIAL PRIMARY KEY,
                        user_mobile VARCHAR(15) REFERENCES users(mobile) ON DELETE CASCADE,
                        notification_type VARCHAR(50) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        data JSONB DEFAULT '{}',
                        delivery_method VARCHAR(20) DEFAULT 'web',
                        status VARCHAR(20) DEFAULT 'pending',
                        scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sent_at TIMESTAMP,
                        expires_at TIMESTAMP,
                        priority INTEGER DEFAULT 5,
                        attempts INTEGER DEFAULT 0,
                        max_attempts INTEGER DEFAULT 3,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # File uploads tracking
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS file_uploads (
                        id SERIAL PRIMARY KEY,
                        user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                        filename VARCHAR(500) NOT NULL,
                        original_filename VARCHAR(500) NOT NULL,
                        file_size BIGINT NOT NULL,
                        mime_type VARCHAR(100),
                        file_hash VARCHAR(128),
                        storage_path TEXT NOT NULL,
                        upload_purpose VARCHAR(100),
                        processed BOOLEAN DEFAULT FALSE,
                        processing_status VARCHAR(50) DEFAULT 'pending',
                        processing_result JSONB,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP
                    );
                """)

            # Create all necessary indexes
            await self.create_indexes(conn)

            # Create triggers for updated_at timestamps
            await self.create_triggers(conn)

            logger.info("✅ All database tables created/verified successfully")

    async def create_indexes(self, conn):
        """Create database indexes for performance optimization"""
        indexes = [
            # User table indexes
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login_attempt);",

            # User profiles indexes
            "CREATE INDEX IF NOT EXISTS idx_profiles_gstin ON user_profiles(gstin);",
            "CREATE INDEX IF NOT EXISTS idx_profiles_company_name ON user_profiles(company_name);",
            "CREATE INDEX IF NOT EXISTS idx_profiles_compliance_score ON user_profiles(compliance_score);",
            "CREATE INDEX IF NOT EXISTS idx_profiles_business_type ON user_profiles(business_type);",

            # GST search history indexes
            "CREATE INDEX IF NOT EXISTS idx_gst_search_user_mobile ON gst_search_history(user_mobile);",
            "CREATE INDEX IF NOT EXISTS idx_gst_search_gstin ON gst_search_history(gstin);",
            "CREATE INDEX IF NOT EXISTS idx_gst_search_created_at ON gst_search_history(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_gst_search_success ON gst_search_history(success);",
            "CREATE INDEX IF NOT EXISTS idx_gst_search_type ON gst_search_history(search_type);",

            # Sessions indexes
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_mobile ON user_sessions(user_mobile);",
            "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at);",
            "CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON user_sessions(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON user_sessions(last_activity);",

            # API usage indexes
            "CREATE INDEX IF NOT EXISTS idx_api_usage_user_mobile ON api_usage_logs(user_mobile);",
            "CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage_logs(endpoint);",
            "CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage_logs(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_api_usage_response_status ON api_usage_logs(response_status);",

            # Error logs indexes
            "CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);",
            "CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_error_logs_user_mobile ON error_logs(user_mobile);",
            "CREATE INDEX IF NOT EXISTS idx_error_logs_resolved ON error_logs(resolved);",
            "CREATE INDEX IF NOT EXISTS idx_error_logs_severity ON error_logs(severity);",

            # System metrics indexes
            "CREATE INDEX IF NOT EXISTS idx_metrics_name_created ON system_metrics(metric_name, created_at);",
            "CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON system_metrics(created_at);",

            # Activity logs indexes
            "CREATE INDEX IF NOT EXISTS idx_activity_user_mobile ON user_activity_logs(user_mobile);",
            "CREATE INDEX IF NOT EXISTS idx_activity_type ON user_activity_logs(activity_type);",
            "CREATE INDEX IF NOT EXISTS idx_activity_created_at ON user_activity_logs(created_at);",

            # Notifications indexes
            "CREATE INDEX IF NOT EXISTS idx_notifications_user_mobile ON notification_queue(user_mobile);",
            "CREATE INDEX IF NOT EXISTS idx_notifications_status ON notification_queue(status);",
            "CREATE INDEX IF NOT EXISTS idx_notifications_scheduled_at ON notification_queue(scheduled_at);",
            "CREATE INDEX IF NOT EXISTS idx_notifications_priority ON notification_queue(priority);",

            # File uploads indexes
            "CREATE INDEX IF NOT EXISTS idx_uploads_user_mobile ON file_uploads(user_mobile);",
            "CREATE INDEX IF NOT EXISTS idx_uploads_processed ON file_uploads(processed);",
            "CREATE INDEX IF NOT EXISTS idx_uploads_created_at ON file_uploads(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_uploads_expires_at ON file_uploads(expires_at);"
        ]

        for index_sql in indexes:
            try:
                await conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")

    async def create_triggers(self, conn):
        """Create database triggers for automatic timestamp updates"""

        # Updated_at trigger function
        await conn.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)

        # Apply trigger to tables with updated_at columns
        tables_with_updated_at = ['users', 'user_profiles']

        for table in tables_with_updated_at:
            await conn.execute(f"""
                DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                CREATE TRIGGER update_{table}_updated_at
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """)

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

    async def verify_user(self, mobile: str,
                          password_hash: str) -> Optional[dict]:
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
                            last_login_attempt = CURRENT_TIMESTAMP
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

    # Logging methods
    async def log_user_activity(self,
                                mobile: str,
                                activity_type: str,
                                activity_data: dict = None,
                                ip_address: str = None,
                                user_agent: str = None):
        """Log user activity"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO user_activity_logs 
                    (user_mobile, activity_type, activity_data, ip_address, user_agent)
                    VALUES ($1, $2, $3, $4, $5)
                """, mobile, activity_type, json.dumps(activity_data or {}),
                    ip_address, user_agent)
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
                        severity: str = "ERROR"):
        """Log application errors"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO error_logs 
                    (error_type, message, stack_trace, user_mobile, additional_data, severity)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, error_type, message, stack_trace, user_mobile,
                    json.dumps(additional_data or {}), severity)
        except Exception as e:
            logger.error(f"Failed to log error: {e}")

    async def cleanup_expired_data(self):
        """Clean up expired data from database"""
        try:
            async with self.get_connection() as conn:
                # Clean expired sessions
                await conn.execute("""
                    DELETE FROM user_sessions 
                    WHERE expires_at < CURRENT_TIMESTAMP
                """)

                # Clean old error logs (keep 30 days)
                await conn.execute("""
                    DELETE FROM error_logs 
                    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days'
                    AND resolved = TRUE
                """)

                # Clean old activity logs (keep 90 days)
                await conn.execute("""
                    DELETE FROM user_activity_logs 
                    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
                """)

                # Clean expired file uploads
                await conn.execute("""
                    DELETE FROM file_uploads 
                    WHERE expires_at < CURRENT_TIMESTAMP
                """)

                # Clean processed notifications (keep 7 days)
                await conn.execute("""
                    DELETE FROM notification_queue 
                    WHERE status = 'sent' 
                    AND sent_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
                """)

                logger.info("✅ Database cleanup completed")

        except Exception as e:
            logger.error(f"❌ Database cleanup failed: {e}")

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

                # Get recent searches (last 7 days)
                recent_searches = await conn.fetchval(
                    """SELECT COUNT(*) FROM search_history 
                       WHERE mobile = $1 AND searched_at >= NOW() - INTERVAL '7 days'""", mobile
                )

                return {
                    "total_searches": search_count or 0,
                    "avg_compliance": round(avg_compliance or 0, 1),
                    "unique_companies": unique_companies or 0,
                    "recent_searches": recent_searches or 0
                }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"total_searches": 0, "avg_compliance": 0, "unique_companies": 0, "recent_searches": 0}

    async def get_user_profile(self, mobile: str) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            async with self.get_connection() as conn:
                user_data = await conn.fetchrow(
                    "SELECT mobile, email, created_at, last_login, profile_data FROM users WHERE mobile = $1", 
                    mobile
                )

                if user_data:
                    return {
                        "mobile": user_data["mobile"],
                        "email": user_data["email"],
                        "created_at": user_data["created_at"],
                        "last_login": user_data["last_login"],
                        "profile_data": user_data["profile_data"] or {}
                    }
                return {}
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return {}

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

    async def get_analytics_data(self, mobile: str) -> Dict[str, Any]:
        """Get analytics data for user"""
        try:
            async with self.get_connection() as conn:
                # Get monthly search trends
                monthly_searches = await conn.fetch(
                    """SELECT DATE_TRUNC('month', searched_at) as month, 
                              COUNT(*) as count
                       FROM search_history 
                       WHERE mobile = $1 
                       GROUP BY month 
                       ORDER BY month DESC 
                       LIMIT 12""", 
                    mobile
                )
                
                # Get compliance score distribution
                compliance_distribution = await conn.fetch(
                    """SELECT 
                         CASE 
                           WHEN compliance_score >= 80 THEN 'Excellent'
                           WHEN compliance_score >= 60 THEN 'Good'
                           WHEN compliance_score >= 40 THEN 'Average'
                           ELSE 'Poor'
                         END as category,
                         COUNT(*) as count
                       FROM search_history 
                       WHERE mobile = $1 
                       GROUP BY category""", 
                    mobile
                )
                
                return {
                    "monthly_searches": [dict(row) for row in monthly_searches],
                    "compliance_distribution": [dict(row) for row in compliance_distribution]
                }
        except Exception as e:
            logger.error(f"Error getting analytics data: {e}")
            return {"monthly_searches": [], "compliance_distribution": []}

    async def save_search_result(self, mobile: str, gstin: str, company_name: str, 
                               search_data: Dict, compliance_score: float, 
                               ai_synopsis: str = None) -> bool:
        """Save search result to history"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    """INSERT INTO search_history 
                       (mobile, gstin, company_name, search_data, compliance_score, ai_synopsis) 
                       VALUES ($1, $2, $3, $4, $5, $6)""",
                    mobile, gstin, company_name, search_data, compliance_score, ai_synopsis
                )
                return True
        except Exception as e:
            logger.error(f"Error saving search result: {e}")
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

    async def delete_session(self, session_token: str) -> bool:
        """Delete user session"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    "DELETE FROM user_sessions WHERE session_id = $1",
                    session_token
                )
                return True
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False

    async def get_session(self, session_token: str) -> Optional[str]:
        """Get user from session token"""
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchrow(
                    """SELECT user_mobile FROM user_sessions 
                       WHERE session_id = $1 AND expires_at > CURRENT_TIMESTAMP""",
                    session_token
                )
                return result["user_mobile"] if result else None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None

    async def create_session(self, mobile: str) -> str:
        """Create new user session"""
        try:
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=30)
            
            async with self.get_connection() as conn:
                await conn.execute(
                    """INSERT INTO user_sessions (session_id, user_mobile, expires_at) 
                       VALUES ($1, $2, $3)""",
                    session_id, mobile, expires_at
                )
                return session_id
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None

    async def verify_user(self, mobile: str, password: str) -> bool:
        """Verify user credentials"""
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchrow(
                    "SELECT password_hash, salt FROM users WHERE mobile = $1",
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
