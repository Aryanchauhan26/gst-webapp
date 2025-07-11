#!/usr/bin/env python3
"""
Database Schema Fix and Migration Script
Fixes column mismatches and ensures all tables have the correct structure
"""

import asyncio
import asyncpg
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

POSTGRES_DSN = "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

class DatabaseSchemaMigration:
    """Handles database schema migrations and fixes"""
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.conn = None
    
    async def connect(self):
        """Connect to database"""
        try:
            self.conn = await asyncpg.connect(self.dsn)
            logger.info("✅ Connected to database successfully")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from database"""
        if self.conn:
            await self.conn.close()
            logger.info("📤 Disconnected from database")
    
    async def check_and_fix_schema(self):
        """Check and fix database schema issues"""
        logger.info("🔍 Checking database schema...")
        
        try:
            # Check if users table exists
            users_exists = await self.conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'users'
                );
            """)
            
            if not users_exists:
                logger.info("Creating users table...")
                await self.create_users_table()
            else:
                logger.info("Users table exists, checking columns...")
                await self.fix_users_table()
            
            # Check and fix other essential tables
            await self.fix_user_profiles_table()
            await self.fix_user_sessions_table()
            await self.fix_search_history_tables()
            await self.fix_system_tables()
            
            logger.info("✅ Database schema check and fix completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Schema check failed: {e}")
            raise
    
    async def create_users_table(self):
        """Create the users table with all required columns"""
        await self.conn.execute("""
            CREATE TABLE users (
                mobile VARCHAR(15) PRIMARY KEY CHECK (mobile ~ '^[+]?[0-9]{10,15}$'),
                password_hash VARCHAR(255) NOT NULL,
                salt VARCHAR(64) NOT NULL,
                email VARCHAR(255) UNIQUE,
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE,
                failed_login_attempts INTEGER DEFAULT 0,
                last_login_attempt TIMESTAMP,
                last_login TIMESTAMP,
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
        logger.info("✅ Users table created successfully")
    
    async def fix_users_table(self):
        """Fix missing columns in users table"""
        # Check for missing columns and add them
        missing_columns = {
            'profile_data': 'JSONB DEFAULT \'{}\'',
            'preferences': 'JSONB DEFAULT \'{}\'',
            'metadata': 'JSONB DEFAULT \'{}\'',
            'is_verified': 'BOOLEAN DEFAULT FALSE',
            'failed_login_attempts': 'INTEGER DEFAULT 0',
            'last_login_attempt': 'TIMESTAMP',
            'account_locked_until': 'TIMESTAMP',
            'last_password_change': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'two_factor_enabled': 'BOOLEAN DEFAULT FALSE',
            'two_factor_secret': 'VARCHAR(32)',
            'backup_codes': 'TEXT[]',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        for column, definition in missing_columns.items():
            column_exists = await self.conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = $1
                );
            """, column)
            
            if not column_exists:
                try:
                    await self.conn.execute(f"ALTER TABLE users ADD COLUMN {column} {definition};")
                    logger.info(f"✅ Added missing column: users.{column}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not add column {column}: {e}")
    
    async def fix_user_profiles_table(self):
        """Create or fix user_profiles table"""
        table_exists = await self.conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'user_profiles'
            );
        """)
        
        if not table_exists:
            await self.conn.execute("""
                CREATE TABLE user_profiles (
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
            logger.info("✅ Created user_profiles table")
    
    async def fix_user_sessions_table(self):
        """Create or fix user_sessions table"""
        table_exists = await self.conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'user_sessions'
            );
        """)
        
        if not table_exists:
            await self.conn.execute("""
                CREATE TABLE user_sessions (
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
            logger.info("✅ Created user_sessions table")
        else:
            # Check for missing columns
            missing_columns = {
                'session_data': 'JSONB DEFAULT \'{}\'',
                'last_activity': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'ip_address': 'INET',
                'user_agent': 'TEXT',
                'is_active': 'BOOLEAN DEFAULT TRUE',
                'device_fingerprint': 'VARCHAR(128)',
                'location_data': 'JSONB'
            }
            
            for column, definition in missing_columns.items():
                column_exists = await self.conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'user_sessions' AND column_name = $1
                    );
                """, column)
                
                if not column_exists:
                    try:
                        await self.conn.execute(f"ALTER TABLE user_sessions ADD COLUMN {column} {definition};")
                        logger.info(f"✅ Added missing column: user_sessions.{column}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not add column {column}: {e}")
    
    async def fix_search_history_tables(self):
        """Create or fix search history tables"""
        # Create search_history table (main one)
        table_exists = await self.conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'search_history'
            );
        """)
        
        if not table_exists:
            await self.conn.execute("""
                CREATE TABLE search_history (
                    id SERIAL PRIMARY KEY,
                    mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                    gstin VARCHAR(15) NOT NULL,
                    company_name TEXT,
                    search_data JSONB,
                    compliance_score DECIMAL(5,2),
                    ai_synopsis TEXT,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time_ms INTEGER,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                );
            """)
            logger.info("✅ Created search_history table")
        
        # Create gst_search_history table (enhanced version)
        table_exists = await self.conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'gst_search_history'
            );
        """)
        
        if not table_exists:
            await self.conn.execute("""
                CREATE TABLE gst_search_history (
                    id SERIAL PRIMARY KEY,
                    user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                    mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                    gstin VARCHAR(15) NOT NULL,
                    company_name TEXT,
                    search_type VARCHAR(50) DEFAULT 'basic',
                    search_params JSONB DEFAULT '{}',
                    search_data JSONB,
                    response_data JSONB,
                    compliance_score DECIMAL(5,2),
                    ai_synopsis TEXT,
                    response_time_ms INTEGER,
                    api_source VARCHAR(100),
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address INET,
                    user_agent TEXT,
                    session_id VARCHAR(128)
                );
            """)
            logger.info("✅ Created gst_search_history table")
    
    async def fix_system_tables(self):
        """Create essential system tables if they don't exist"""
        
        # API usage logs
        table_exists = await self.conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'api_usage_logs'
            );
        """)
        
        if not table_exists:
            await self.conn.execute("""
                CREATE TABLE api_usage_logs (
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
            logger.info("✅ Created api_usage_logs table")
        
        # Error logs
        table_exists = await self.conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'error_logs'
            );
        """)
        
        if not table_exists:
            await self.conn.execute("""
                CREATE TABLE error_logs (
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
            logger.info("✅ Created error_logs table")
        
        # System metrics
        table_exists = await self.conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'system_metrics'
            );
        """)
        
        if not table_exists:
            await self.conn.execute("""
                CREATE TABLE system_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value DECIMAL(15,4),
                    metric_unit VARCHAR(20),
                    tags JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info("✅ Created system_metrics table")
    
    async def create_indexes(self):
        """Create essential indexes for performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_search_history_mobile ON search_history(mobile);",
            "CREATE INDEX IF NOT EXISTS idx_search_history_gstin ON search_history(gstin);",
            "CREATE INDEX IF NOT EXISTS idx_search_history_searched_at ON search_history(searched_at);",
            "CREATE INDEX IF NOT EXISTS idx_gst_search_user_mobile ON gst_search_history(user_mobile);",
            "CREATE INDEX IF NOT EXISTS idx_gst_search_gstin ON gst_search_history(gstin);",
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_mobile ON user_sessions(user_mobile);",
            "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at);",
            "CREATE INDEX IF NOT EXISTS idx_api_usage_user_mobile ON api_usage_logs(user_mobile);",
            "CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage_logs(created_at);",
        ]
        
        for index_sql in indexes:
            try:
                await self.conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"⚠️ Could not create index: {e}")
        
        logger.info("✅ Indexes created successfully")
    
    async def verify_schema(self):
        """Verify that all required tables and columns exist"""
        logger.info("🔍 Verifying database schema...")
        
        # Check critical tables
        required_tables = [
            'users', 'user_profiles', 'user_sessions', 
            'search_history', 'gst_search_history',
            'api_usage_logs', 'error_logs', 'system_metrics'
        ]
        
        for table in required_tables:
            exists = await self.conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = $1
                );
            """, table)
            
            if exists:
                logger.info(f"✅ Table '{table}' exists")
            else:
                logger.error(f"❌ Table '{table}' missing")
        
        # Check critical columns in users table
        required_user_columns = [
            'mobile', 'password_hash', 'salt', 'email', 
            'profile_data', 'created_at', 'last_login'
        ]
        
        for column in required_user_columns:
            exists = await self.conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = $1
                );
            """, column)
            
            if exists:
                logger.info(f"✅ Column 'users.{column}' exists")
            else:
                logger.error(f"❌ Column 'users.{column}' missing")
        
        logger.info("✅ Schema verification completed")

async def main():
    """Run database schema migration"""
    logger.info("🚀 Starting Database Schema Migration...")
    logger.info("=" * 60)
    
    migration = DatabaseSchemaMigration(POSTGRES_DSN)
    
    try:
        await migration.connect()
        await migration.check_and_fix_schema()
        await migration.create_indexes()
        await migration.verify_schema()
        
        logger.info("=" * 60)
        logger.info("✅ Database schema migration completed successfully!")
        logger.info("🎉 Your database is now properly configured!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await migration.disconnect()

if __name__ == "__main__":
    asyncio.run(main())