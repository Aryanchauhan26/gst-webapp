# Enhanced Database Manager with Connection Pooling and Error Handling
import asyncio
import asyncpg
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import json

logger = logging.getLogger(__name__)


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

    async def initialize(self):
        """Initialize database with proper error handling"""
        try:
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

            # Redis connection (optional)
            if self.redis_url:
                try:
                    import redis.asyncio as redis
                    self.redis_client = redis.from_url(
                        self.redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                        retry_on_timeout=True,
                        health_check_interval=30)
                    await self.redis_client.ping()
                    logger.info("✅ Redis connected successfully")
                except Exception as e:
                    logger.warning(
                        f"Redis connection failed, using memory cache: {e}")
                    self.redis_client = None

            # Ensure all tables exist
            await self.ensure_tables()
            logger.info("✅ Database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def ensure_tables(self):
        """Create all required tables with proper indexes"""
        async with self.pool.acquire() as conn:
            # Users table with enhanced constraints
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    mobile VARCHAR(15) PRIMARY KEY CHECK (mobile ~ '^\+?[1-9]\d{1,14}$'),
                    password_hash VARCHAR(255) NOT NULL,
                    salt VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    failed_login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                );
            """)

            # Sessions table with proper cleanup
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token VARCHAR(255) PRIMARY KEY,
                    mobile VARCHAR(15) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT,
                    ip_address INET,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)

            # Search history with improved indexing
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    mobile VARCHAR(15) NOT NULL,
                    gstin VARCHAR(15) NOT NULL CHECK (gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'),
                    company_name TEXT,
                    compliance_score DECIMAL(5,2) CHECK (compliance_score >= 0 AND compliance_score <= 100),
                    search_data JSONB,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time_ms INTEGER,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)

            # User profiles
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    mobile VARCHAR(15) PRIMARY KEY,
                    display_name VARCHAR(100),
                    company VARCHAR(200),
                    email VARCHAR(255) CHECK (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
                    designation VARCHAR(100),
                    avatar_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)

            # Loan applications
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS loan_applications (
                    id SERIAL PRIMARY KEY,
                    user_mobile VARCHAR(15) NOT NULL,
                    razorpay_application_id VARCHAR(100),
                    gstin VARCHAR(15) NOT NULL,
                    company_name TEXT NOT NULL,
                    loan_amount DECIMAL(15,2) NOT NULL CHECK (loan_amount > 0),
                    purpose TEXT NOT NULL,
                    tenure_months INTEGER NOT NULL CHECK (tenure_months > 0),
                    annual_turnover DECIMAL(15,2) NOT NULL CHECK (annual_turnover > 0),
                    monthly_revenue DECIMAL(15,2) NOT NULL CHECK (monthly_revenue > 0),
                    compliance_score DECIMAL(5,2) NOT NULL CHECK (compliance_score >= 0 AND compliance_score <= 100),
                    business_vintage_months INTEGER NOT NULL CHECK (business_vintage_months >= 0),
                    risk_score DECIMAL(5,2),
                    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'disbursed', 'closed')),
                    application_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)

            # Error logs for monitoring
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    id SERIAL PRIMARY KEY,
                    error_type VARCHAR(100) NOT NULL,
                    message TEXT NOT NULL,
                    stack_trace TEXT,
                    url TEXT,
                    user_agent TEXT,
                    user_mobile VARCHAR(15),
                    ip_address INET,
                    request_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    severity VARCHAR(20) DEFAULT 'error' CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
                    resolved BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_mobile) REFERENCES users(mobile) ON DELETE SET NULL
                );
            """)

            # Create optimized indexes
            await self._create_indexes(conn)

    async def _create_indexes(self, conn):
        """Create database indexes for optimal performance"""
        indexes = [
            # Session management
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_expires ON sessions(expires_at) WHERE expires_at > CURRENT_TIMESTAMP",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_mobile_active ON sessions(mobile, last_activity DESC)",

            # Search history optimization
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_search_history_mobile_date ON search_history(mobile, searched_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_search_history_gstin ON search_history(gstin)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_search_history_compliance ON search_history(compliance_score DESC)",

            # User management
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login ON users(last_login DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active ON users(is_active, created_at)",

            # Loan applications
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_loan_applications_user_status ON loan_applications(user_mobile, status, created_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_loan_applications_gstin ON loan_applications(gstin)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_loan_applications_status_date ON loan_applications(status, created_at)",

            # Error monitoring
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_error_logs_type_severity ON error_logs(error_type, severity)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_error_logs_unresolved ON error_logs(resolved, created_at) WHERE resolved = FALSE"
        ]

        for index_sql in indexes:
            try:
                await conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection with automatic retry and health check"""
        retries = 3
        for attempt in range(retries):
            try:
                if not self.pool:
                    await self.initialize()

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

    async def create_user(self, mobile: str, password_hash: str,
                          salt: str) -> bool:
        """Create new user with enhanced validation"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO users (mobile, password_hash, salt)
                    VALUES ($1, $2, $3)
                """, mobile, password_hash, salt)

                # Initialize user profile
                await conn.execute(
                    """
                    INSERT INTO user_profiles (mobile, display_name)
                    VALUES ($1, $2)
                """, mobile, f"User {mobile[-4:]}")

                logger.info(f"User created successfully: {mobile}")
                return True

        except asyncpg.UniqueViolationError:
            logger.warning(f"User already exists: {mobile}")
            return False
        except Exception as e:
            logger.error(f"User creation failed: {e}")
            return False

    async def verify_user(self, mobile: str,
                          password_hash: str) -> Optional[dict]:
        """Verify user credentials with security features"""
        try:
            async with self.get_connection() as conn:
                # Check if account is locked
                user = await conn.fetchrow(
                    """
                    SELECT mobile, password_hash, salt, failed_login_attempts, 
                           locked_until, is_active, last_login
                    FROM users 
                    WHERE mobile = $1
                """, mobile)

                if not user:
                    return None

                if not user['is_active']:
                    logger.warning(
                        f"Login attempt on inactive account: {mobile}")
                    return None

                # Check if account is locked
                if user['locked_until'] and user[
                        'locked_until'] > datetime.now():
                    logger.warning(
                        f"Login attempt on locked account: {mobile}")
                    return None

                # Verify password (implement your password verification logic here)
                # This is a placeholder - implement proper password verification
                if user['password_hash'] == password_hash:
                    # Reset failed attempts and update last login
                    await conn.execute(
                        """
                        UPDATE users 
                        SET failed_login_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP
                        WHERE mobile = $1
                    """, mobile)

                    return dict(user)
                else:
                    # Increment failed attempts
                    failed_attempts = (user['failed_login_attempts'] or 0) + 1
                    lock_until = None

                    if failed_attempts >= 5:
                        lock_until = datetime.now() + timedelta(minutes=30)

                    await conn.execute(
                        """
                        UPDATE users 
                        SET failed_login_attempts = $2, locked_until = $3
                        WHERE mobile = $1
                    """, mobile, failed_attempts, lock_until)

                    return None

        except Exception as e:
            logger.error(f"User verification failed: {e}")
            return None

    async def save_search_history(self,
                                  mobile: str,
                                  gstin: str,
                                  company_name: str,
                                  compliance_score: float,
                                  search_data: dict = None,
                                  response_time_ms: int = None) -> bool:
        """Save search history with deduplication"""
        try:
            async with self.get_connection() as conn:
                # Check for recent duplicate
                recent_search = await conn.fetchrow(
                    """
                    SELECT id FROM search_history 
                    WHERE mobile = $1 AND gstin = $2 
                    AND searched_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
                    ORDER BY searched_at DESC LIMIT 1
                """, mobile, gstin)

                if recent_search:
                    # Update existing record instead of creating duplicate
                    await conn.execute(
                        """
                        UPDATE search_history 
                        SET company_name = $3, compliance_score = $4, 
                            search_data = $5, searched_at = CURRENT_TIMESTAMP,
                            response_time_ms = $6
                        WHERE id = $1
                    """, recent_search['id'], company_name, compliance_score,
                        json.dumps(search_data) if search_data else None,
                        response_time_ms)
                else:
                    # Create new record
                    await conn.execute(
                        """
                        INSERT INTO search_history 
                        (mobile, gstin, company_name, compliance_score, search_data, response_time_ms)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, mobile, gstin, company_name, compliance_score,
                        json.dumps(search_data) if search_data else None,
                        response_time_ms)

                return True

        except Exception as e:
            logger.error(f"Save search history failed: {e}")
            return False

    async def get_user_stats(self, mobile: str) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        try:
            async with self.get_connection() as conn:
                stats = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(DISTINCT gstin) as unique_companies,
                        COUNT(*) as total_searches,
                        AVG(compliance_score) as avg_compliance,
                        MAX(searched_at) as last_search,
                        AVG(response_time_ms) as avg_response_time
                    FROM search_history 
                    WHERE mobile = $1 AND searched_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
                """, mobile)

                loan_stats = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total_applications,
                        COUNT(*) FILTER (WHERE status = 'approved') as approved_count,
                        SUM(loan_amount) FILTER (WHERE status IN ('approved', 'disbursed')) as approved_amount
                    FROM loan_applications 
                    WHERE user_mobile = $1
                """, mobile)

                return {
                    'total_searches': stats['total_searches'] or 0,
                    'unique_companies': stats['unique_companies'] or 0,
                    'avg_compliance': float(stats['avg_compliance'] or 0),
                    'last_search': stats['last_search'],
                    'avg_response_time': stats['avg_response_time'] or 0,
                    'loan_applications': loan_stats['total_applications'] or 0,
                    'approved_loans': loan_stats['approved_count'] or 0,
                    'approved_amount': float(loan_stats['approved_amount']
                                             or 0)
                }

        except Exception as e:
            logger.error(f"Get user stats failed: {e}")
            return {}

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions and old data"""
        try:
            async with self.get_connection() as conn:
                # Remove expired sessions
                expired_sessions = await conn.execute("""
                    DELETE FROM sessions 
                    WHERE expires_at < CURRENT_TIMESTAMP
                """)

                # Remove old search history (keep last 90 days)
                old_searches = await conn.execute("""
                    DELETE FROM search_history 
                    WHERE searched_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
                """)

                # Remove resolved error logs older than 30 days
                old_errors = await conn.execute("""
                    DELETE FROM error_logs 
                    WHERE resolved = TRUE AND created_at < CURRENT_TIMESTAMP - INTERVAL '30 days'
                """)

                logger.info(
                    f"Cleanup completed: {expired_sessions} sessions, {old_searches} searches, {old_errors} errors removed"
                )

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    async def get_health_status(self) -> Dict[str, Any]:
        """Get database health status"""
        try:
            async with self.get_connection() as conn:
                # Check basic connectivity
                await conn.execute("SELECT 1")

                # Get connection pool stats
                pool_stats = {
                    'size': self.pool.get_size(),
                    'max_size': self.pool.get_max_size(),
                    'min_size': self.pool.get_min_size(),
                    'idle_connections': self.pool.get_idle_size()
                }

                # Get database stats
                db_stats = await conn.fetchrow("""
                    SELECT 
                        (SELECT COUNT(*) FROM users WHERE is_active = TRUE) as active_users,
                        (SELECT COUNT(*) FROM sessions WHERE expires_at > CURRENT_TIMESTAMP) as active_sessions,
                        (SELECT COUNT(*) FROM search_history WHERE searched_at > CURRENT_TIMESTAMP - INTERVAL '24 hours') as recent_searches
                """)

                return {
                    'status': 'healthy',
                    'pool_stats': pool_stats,
                    'database_stats': dict(db_stats),
                    'redis_connected': bool(self.redis_client),
                    'timestamp': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def close(self):
        """Close all database connections"""
        if self.pool:
            await self.pool.close()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Database connections closed")
