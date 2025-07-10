#!/usr/bin/env python3
"""
Complete Database Schema Fix for GST Intelligence Platform
This fixes all inconsistencies and missing elements
"""

import asyncio
import asyncpg
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

POSTGRES_DSN = "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

async def fix_complete_database_schema():
    """Complete database schema fix"""
    
    conn = await asyncpg.connect(POSTGRES_DSN)
    
    try:
        logger.info("🔧 Starting complete database schema fix...")
        
        # Start transaction
        async with conn.transaction():
            
            # 1. Drop and recreate users table with correct structure
            logger.info("📋 Creating users table...")
            await conn.execute("DROP TABLE IF EXISTS user_sessions CASCADE;")
            await conn.execute("DROP TABLE IF EXISTS gst_search_history CASCADE;")
            await conn.execute("DROP TABLE IF EXISTS search_history CASCADE;")
            await conn.execute("DROP TABLE IF EXISTS user_profiles CASCADE;")
            await conn.execute("DROP TABLE IF EXISTS users CASCADE;")
            
            await conn.execute("""
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

            # 2. Create user_profiles table
            logger.info("📋 Creating user_profiles table...")
            await conn.execute("""
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

            # 3. Create user_sessions table with correct structure
            logger.info("📋 Creating user_sessions table...")
            await conn.execute("""
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

            # 4. Create search history table (main one)
            logger.info("📋 Creating search_history table...")
            await conn.execute("""
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

            # 5. Create gst_search_history table (enhanced version)
            logger.info("📋 Creating gst_search_history table...")
            await conn.execute("""
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

            # 6. Create other essential tables
            logger.info("📋 Creating additional tables...")
            
            # API usage tracking
            await conn.execute("""
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

            # Error logging
            await conn.execute("""
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

            # User activity logs
            await conn.execute("""
                CREATE TABLE user_activity_logs (
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
                CREATE TABLE notification_queue (
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
                CREATE TABLE file_uploads (
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

            # System health metrics
            await conn.execute("""
                CREATE TABLE system_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value DECIMAL(15,4),
                    metric_unit VARCHAR(20),
                    tags JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 7. Create all indexes
            logger.info("📋 Creating indexes...")
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

                # Search history indexes
                "CREATE INDEX IF NOT EXISTS idx_search_history_mobile ON search_history(mobile);",
                "CREATE INDEX IF NOT EXISTS idx_search_history_gstin ON search_history(gstin);",
                "CREATE INDEX IF NOT EXISTS idx_search_history_searched_at ON search_history(searched_at);",
                "CREATE INDEX IF NOT EXISTS idx_search_history_success ON search_history(success);",

                # GST search history indexes
                "CREATE INDEX IF NOT EXISTS idx_gst_search_user_mobile ON gst_search_history(user_mobile);",
                "CREATE INDEX IF NOT EXISTS idx_gst_search_mobile ON gst_search_history(mobile);",
                "CREATE INDEX IF NOT EXISTS idx_gst_search_gstin ON gst_search_history(gstin);",
                "CREATE INDEX IF NOT EXISTS idx_gst_search_created_at ON gst_search_history(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_gst_search_searched_at ON gst_search_history(searched_at);",
                "CREATE INDEX IF NOT EXISTS idx_gst_search_success ON gst_search_history(success);",

                # Sessions indexes
                "CREATE INDEX IF NOT EXISTS idx_sessions_user_mobile ON user_sessions(user_mobile);",
                "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at);",
                "CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON user_sessions(is_active);",
                "CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON user_sessions(last_activity);",

                # API usage indexes
                "CREATE INDEX IF NOT EXISTS idx_api_usage_user_mobile ON api_usage_logs(user_mobile);",
                "CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage_logs(endpoint);",
                "CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage_logs(created_at);",

                # Error logs indexes
                "CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);",
                "CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_error_logs_user_mobile ON error_logs(user_mobile);",

                # Activity logs indexes
                "CREATE INDEX IF NOT EXISTS idx_activity_user_mobile ON user_activity_logs(user_mobile);",
                "CREATE INDEX IF NOT EXISTS idx_activity_type ON user_activity_logs(activity_type);",
                "CREATE INDEX IF NOT EXISTS idx_activity_created_at ON user_activity_logs(created_at);",
            ]

            for index_sql in indexes:
                await conn.execute(index_sql)

            # 8. Create triggers
            logger.info("📋 Creating triggers...")
            await conn.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)

            # Apply triggers
            tables_with_updated_at = ['users', 'user_profiles']
            for table in tables_with_updated_at:
                await conn.execute(f"""
                    DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                    CREATE TRIGGER update_{table}_updated_at
                        BEFORE UPDATE ON {table}
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                """)

        logger.info("✅ Database schema fixed successfully!")
        
        # Verify the migration
        logger.info("📋 Verifying migration...")
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        logger.info(f"✅ Created {len(tables)} tables:")
        for table in tables:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table['table_name']}")
            logger.info(f"  - {table['table_name']}: {count} records")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_complete_database_schema())