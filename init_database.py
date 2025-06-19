#!/usr/bin/env python3
"""
Database initialization script for GST Intelligence Platform
Run this before starting the application for the first time
"""

import asyncio
import asyncpg
<<<<<<< HEAD
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POSTGRES_DSN = "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

async def initialize_database():
    """Initialize database with all required tables"""
    try:
        conn = await asyncpg.connect(dsn=POSTGRES_DSN)
        logger.info("✅ Connected to database successfully")
        
        # Create users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                mobile VARCHAR(10) PRIMARY KEY,
                password_hash VARCHAR(128) NOT NULL,
                salt VARCHAR(32) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
        """)
        logger.info("✅ Users table created/verified")
        
        # Create sessions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_token VARCHAR(64) PRIMARY KEY,
                mobile VARCHAR(10) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
            );
        """)
        logger.info("✅ Sessions table created/verified")
        
        # Create search_history table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                mobile VARCHAR(10) NOT NULL,
                gstin VARCHAR(15) NOT NULL,
                company_name TEXT NOT NULL,
                compliance_score DECIMAL(5,2),
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
            );
        """)
        logger.info("✅ Search history table created/verified")
        
        # Create user_preferences table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                mobile VARCHAR(10) PRIMARY KEY,
                preferences JSONB NOT NULL DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
            );
        """)
        logger.info("✅ User preferences table created/verified")
        
        # Create indexes for better performance
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_search_history_mobile ON search_history(mobile);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_search_history_searched_at ON search_history(searched_at);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_preferences_mobile ON user_preferences(mobile);")
        logger.info("✅ Database indexes created/verified")
        
        # Clean up old sessions
        await conn.execute("DELETE FROM sessions WHERE expires_at < NOW();")
        logger.info("✅ Cleaned up expired sessions")
        
        await conn.close()
        logger.info("🎉 Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(initialize_database())
=======
import os
import sys
import logging
from datetime import datetime, timedelta
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
POSTGRES_DSN = os.getenv(
    "DATABASE_URL", 
    "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
)

class DatabaseInitializer:
    def __init__(self, dsn: str = POSTGRES_DSN):
        self.dsn = dsn
        self.conn = None

    async def connect(self):
        """Establish database connection"""
        try:
            self.conn = await asyncpg.connect(self.dsn)
            logger.info("✅ Database connection established")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            return False

    async def disconnect(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            logger.info("🔌 Database connection closed")

    async def create_tables(self):
        """Create all required tables"""
        logger.info("🏗️  Creating database tables...")
        
        try:
            # Drop existing tables if recreating (uncomment if needed)
            # await self.drop_tables()
            
            # Users table - Core user management
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    mobile VARCHAR(10) PRIMARY KEY,
                    password_hash VARCHAR(255) NOT NULL,
                    salt VARCHAR(64) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    failed_login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP NULL,
                    
                    -- Indexes
                    INDEX idx_users_mobile (mobile),
                    INDEX idx_users_created_at (created_at),
                    INDEX idx_users_last_login (last_login)
                );
            """)
            logger.info("✅ Users table created")

            # Sessions table - User session management
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token VARCHAR(64) PRIMARY KEY,
                    mobile VARCHAR(10) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT,
                    ip_address INET,
                    
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE,
                    
                    -- Indexes
                    INDEX idx_sessions_mobile (mobile),
                    INDEX idx_sessions_expires (expires_at),
                    INDEX idx_sessions_created (created_at)
                );
            """)
            logger.info("✅ Sessions table created")

            # Search history table - Track all GSTIN searches
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    mobile VARCHAR(10) NOT NULL,
                    gstin VARCHAR(15) NOT NULL,
                    company_name TEXT NOT NULL,
                    compliance_score DECIMAL(5,2),
                    search_result JSONB,
                    ai_analysis JSONB,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_time_ms INTEGER,
                    api_source VARCHAR(50) DEFAULT 'rapidapi',
                    
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE,
                    
                    -- Indexes
                    INDEX idx_search_mobile (mobile),
                    INDEX idx_search_gstin (gstin),
                    INDEX idx_search_date (searched_at),
                    INDEX idx_search_company (company_name),
                    INDEX idx_search_score (compliance_score)
                );
            """)
            logger.info("✅ Search history table created")

            # User profiles table - Extended user information
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    mobile VARCHAR(10) PRIMARY KEY,
                    display_name VARCHAR(100),
                    email VARCHAR(255),
                    company VARCHAR(255),
                    designation VARCHAR(100),
                    avatar_url TEXT,
                    preferences JSONB DEFAULT '{}',
                    subscription_tier VARCHAR(20) DEFAULT 'free',
                    api_quota_used INTEGER DEFAULT 0,
                    api_quota_limit INTEGER DEFAULT 100,
                    quota_reset_date DATE DEFAULT CURRENT_DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE,
                    
                    -- Indexes
                    INDEX idx_profiles_email (email),
                    INDEX idx_profiles_company (company),
                    INDEX idx_profiles_tier (subscription_tier)
                );
            """)
            logger.info("✅ User profiles table created")

            # Analytics table - Track user activity patterns
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_analytics (
                    id SERIAL PRIMARY KEY,
                    mobile VARCHAR(10) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    event_data JSONB,
                    session_id VARCHAR(64),
                    ip_address INET,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE,
                    
                    -- Indexes
                    INDEX idx_analytics_mobile (mobile),
                    INDEX idx_analytics_event (event_type),
                    INDEX idx_analytics_date (created_at),
                    INDEX idx_analytics_session (session_id)
                );
            """)
            logger.info("✅ User analytics table created")

            # System logs table - Application logging
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id SERIAL PRIMARY KEY,
                    level VARCHAR(10) NOT NULL,
                    message TEXT NOT NULL,
                    module VARCHAR(50),
                    function_name VARCHAR(100),
                    user_mobile VARCHAR(10),
                    extra_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Indexes
                    INDEX idx_logs_level (level),
                    INDEX idx_logs_date (created_at),
                    INDEX idx_logs_user (user_mobile),
                    INDEX idx_logs_module (module)
                );
            """)
            logger.info("✅ System logs table created")

            # Rate limiting table - API rate limiting
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id VARCHAR(255) PRIMARY KEY,
                    requests_count INTEGER DEFAULT 1,
                    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_request TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Indexes
                    INDEX idx_rate_limits_window (window_start),
                    INDEX idx_rate_limits_last (last_request)
                );
            """)
            logger.info("✅ Rate limits table created")

            # Favorites table - User's favorite companies
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_favorites (
                    id SERIAL PRIMARY KEY,
                    mobile VARCHAR(10) NOT NULL,
                    gstin VARCHAR(15) NOT NULL,
                    company_name TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE,
                    UNIQUE(mobile, gstin),
                    
                    -- Indexes
                    INDEX idx_favorites_mobile (mobile),
                    INDEX idx_favorites_gstin (gstin),
                    INDEX idx_favorites_date (added_at)
                );
            """)
            logger.info("✅ User favorites table created")

            logger.info("🎉 All tables created successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
            raise

    async def create_indexes(self):
        """Create additional performance indexes"""
        logger.info("🔍 Creating additional indexes...")
        
        try:
            # Composite indexes for better query performance
            await self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_user_date 
                ON search_history(mobile, searched_at DESC);
            """)
            
            await self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_gstin_date 
                ON search_history(gstin, searched_at DESC);
            """)
            
            await self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_active 
                ON sessions(mobile, expires_at) WHERE expires_at > NOW();
            """)
            
            # Full-text search index for company names
            await self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_company_fulltext 
                ON search_history USING gin(to_tsvector('english', company_name));
            """)
            
            logger.info("✅ Additional indexes created")
            
        except Exception as e:
            logger.error(f"❌ Error creating indexes: {e}")
            raise

    async def create_functions(self):
        """Create useful database functions"""
        logger.info("⚙️  Creating database functions...")
        
        try:
            # Function to clean old sessions
            await self.conn.execute("""
                CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
                RETURNS INTEGER AS $$
                DECLARE
                    deleted_count INTEGER;
                BEGIN
                    DELETE FROM sessions WHERE expires_at < NOW();
                    GET DIAGNOSTICS deleted_count = ROW_COUNT;
                    RETURN deleted_count;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            # Function to update user last activity
            await self.conn.execute("""
                CREATE OR REPLACE FUNCTION update_user_activity(user_mobile VARCHAR(10))
                RETURNS VOID AS $$
                BEGIN
                    UPDATE users SET last_login = NOW() WHERE mobile = user_mobile;
                    UPDATE sessions SET last_accessed = NOW() 
                    WHERE mobile = user_mobile AND expires_at > NOW();
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            # Function to get user statistics
            await self.conn.execute("""
                CREATE OR REPLACE FUNCTION get_user_stats(user_mobile VARCHAR(10))
                RETURNS TABLE(
                    total_searches BIGINT,
                    unique_companies BIGINT,
                    avg_compliance_score NUMERIC,
                    last_search_date TIMESTAMP,
                    account_age_days INTEGER
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        COUNT(*)::BIGINT as total_searches,
                        COUNT(DISTINCT gstin)::BIGINT as unique_companies,
                        AVG(compliance_score) as avg_compliance_score,
                        MAX(searched_at) as last_search_date,
                        EXTRACT(DAYS FROM NOW() - u.created_at)::INTEGER as account_age_days
                    FROM search_history sh
                    JOIN users u ON sh.mobile = u.mobile
                    WHERE sh.mobile = user_mobile;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            logger.info("✅ Database functions created")
            
        except Exception as e:
            logger.error(f"❌ Error creating functions: {e}")
            raise

    async def insert_sample_data(self):
        """Insert sample data for testing (optional)"""
        logger.info("📊 Inserting sample data...")
        
        try:
            # Check if sample data already exists
            user_count = await self.conn.fetchval("SELECT COUNT(*) FROM users")
            
            if user_count > 0:
                logger.info("⚠️  Sample data already exists, skipping...")
                return
            
            # Sample user for testing
            await self.conn.execute("""
                INSERT INTO users (mobile, password_hash, salt) 
                VALUES ('9999999999', 
                       'test_hash_placeholder', 
                       'test_salt_placeholder')
                ON CONFLICT (mobile) DO NOTHING;
            """)
            
            # Sample user profile
            await self.conn.execute("""
                INSERT INTO user_profiles (mobile, display_name, email, company) 
                VALUES ('9999999999', 
                       'Test User', 
                       'test@example.com', 
                       'Test Company Ltd.')
                ON CONFLICT (mobile) DO NOTHING;
            """)
            
            logger.info("✅ Sample data inserted")
            
        except Exception as e:
            logger.error(f"❌ Error inserting sample data: {e}")
            raise

    async def create_triggers(self):
        """Create database triggers for automation"""
        logger.info("🔄 Creating database triggers...")
        
        try:
            # Trigger to update user profile timestamp
            await self.conn.execute("""
                CREATE OR REPLACE FUNCTION update_profile_timestamp()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                
                DROP TRIGGER IF EXISTS trigger_update_profile_timestamp ON user_profiles;
                CREATE TRIGGER trigger_update_profile_timestamp
                    BEFORE UPDATE ON user_profiles
                    FOR EACH ROW
                    EXECUTE FUNCTION update_profile_timestamp();
            """)
            
            # Trigger to reset API quota monthly
            await self.conn.execute("""
                CREATE OR REPLACE FUNCTION reset_api_quota()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF NEW.quota_reset_date <= CURRENT_DATE THEN
                        NEW.api_quota_used = 0;
                        NEW.quota_reset_date = CURRENT_DATE + INTERVAL '1 month';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                
                DROP TRIGGER IF EXISTS trigger_reset_api_quota ON user_profiles;
                CREATE TRIGGER trigger_reset_api_quota
                    BEFORE UPDATE ON user_profiles
                    FOR EACH ROW
                    EXECUTE FUNCTION reset_api_quota();
            """)
            
            logger.info("✅ Database triggers created")
            
        except Exception as e:
            logger.error(f"❌ Error creating triggers: {e}")
            raise

    async def verify_setup(self):
        """Verify database setup is correct"""
        logger.info("🔍 Verifying database setup...")
        
        try:
            # Check all tables exist
            tables = await self.conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            expected_tables = {
                'users', 'sessions', 'search_history', 'user_profiles',
                'user_analytics', 'system_logs', 'rate_limits', 'user_favorites'
            }
            
            existing_tables = {row['table_name'] for row in tables}
            missing_tables = expected_tables - existing_tables
            
            if missing_tables:
                logger.error(f"❌ Missing tables: {missing_tables}")
                return False
            
            # Check functions exist
            functions = await self.conn.fetch("""
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_schema = 'public' 
                AND routine_type = 'FUNCTION';
            """)
            
            function_names = {row['routine_name'] for row in functions}
            expected_functions = {
                'cleanup_expired_sessions', 'update_user_activity', 'get_user_stats'
            }
            
            if not expected_functions.issubset(function_names):
                logger.warning("⚠️  Some functions may be missing")
            
            # Test basic operations
            await self.conn.execute("SELECT 1;")
            logger.info("✅ Database verification completed successfully")
            
            # Print summary
            logger.info(f"📊 Database Summary:")
            logger.info(f"   - Tables: {len(existing_tables)}")
            logger.info(f"   - Functions: {len(function_names)}")
            logger.info(f"   - Connection: Active")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Database verification failed: {e}")
            return False

    async def drop_tables(self):
        """Drop all tables (use with caution!)"""
        logger.warning("⚠️  DROPPING ALL TABLES - This will delete all data!")
        
        try:
            # Drop tables in correct order (considering foreign keys)
            tables_to_drop = [
                'user_analytics', 'user_favorites', 'search_history',
                'user_profiles', 'sessions', 'rate_limits', 'system_logs', 'users'
            ]
            
            for table in tables_to_drop:
                await self.conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                logger.info(f"🗑️  Dropped table: {table}")
                
            logger.warning("💥 All tables dropped!")
            
        except Exception as e:
            logger.error(f"❌ Error dropping tables: {e}")
            raise

async def main():
    """Main initialization function"""
    print("🚀 GST Intelligence Platform - Database Initialization")
    print("=" * 60)
    
    # Parse command line arguments
    force_recreate = '--force' in sys.argv
    skip_sample = '--no-sample' in sys.argv
    drop_first = '--drop' in sys.argv
    
    db_init = DatabaseInitializer()
    
    try:
        # Connect to database
        print("🔗 Connecting to database...")
        if not await db_init.connect():
            print("❌ Failed to connect to database. Check your connection string.")
            sys.exit(1)
        
        # Drop tables if requested
        if drop_first:
            print("🗑️  Dropping existing tables...")
            await db_init.drop_tables()
        
        # Create tables
        print("🏗️  Creating database tables...")
        await db_init.create_tables()
        
        # Create indexes
        print("🔍 Creating database indexes...")
        await db_init.create_indexes()
        
        # Create functions
        print("⚙️  Creating database functions...")
        await db_init.create_functions()
        
        # Create triggers
        print("🔄 Creating database triggers...")
        await db_init.create_triggers()
        
        # Insert sample data if requested
        if not skip_sample:
            print("📊 Inserting sample data...")
            await db_init.insert_sample_data()
        
        # Verify setup
        print("🔍 Verifying database setup...")
        if await db_init.verify_setup():
            print("✅ Database initialization completed successfully!")
            print("\n🎉 Your GST Intelligence Platform is ready to use!")
            print("\nNext steps:")
            print("1. Set your environment variables (API keys)")
            print("2. Run: python start.py")
            print("3. Visit: http://localhost:8000")
        else:
            print("❌ Database verification failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"💥 Database initialization failed: {e}")
        sys.exit(1)
    finally:
        await db_init.disconnect()

if __name__ == "__main__":
    print("Usage:")
    print("  python init_database.py           # Normal initialization")
    print("  python init_database.py --force   # Force recreate")
    print("  python init_database.py --drop    # Drop tables first")
    print("  python init_database.py --no-sample # Skip sample data")
    print()
    
    asyncio.run(main())
>>>>>>> c532489b53e866b4caaacf4b11866da31089f9c3
