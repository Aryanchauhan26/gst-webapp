#!/usr/bin/env python3
"""
Database Schema Migration to Fix Missing Columns - FIXED VERSION
This will update your existing database to match application requirements
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

async def execute_safely(conn, sql, description=""):
    """Execute SQL safely with error handling"""
    try:
        await conn.execute(sql)
        if description:
            logger.info(f"  ✅ {description}")
        return True
    except Exception as e:
        logger.warning(f"  ⚠️ {description}: {e}")
        return False

async def fix_database_schema():
    """Fix database schema to match application requirements"""
    
    conn = await asyncpg.connect(POSTGRES_DSN)
    
    try:
        logger.info("🔧 Starting database schema migration...")
        
        # 1. Fix users table
        logger.info("📋 Fixing users table...")
        
        user_fixes = [
            ("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;", "Added is_active column"),
            ("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;", "Added is_verified column"),
            ("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;", "Added failed_login_attempts column"),
            ("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_attempt TIMESTAMP;", "Added last_login_attempt column"),
            ("ALTER TABLE users ADD COLUMN IF NOT EXISTS account_locked_until TIMESTAMP;", "Added account_locked_until column"),
            ("ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;", "Added updated_at column"),
            ("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_password_change TIMESTAMP DEFAULT CURRENT_TIMESTAMP;", "Added last_password_change column"),
        ]
        
        for sql, desc in user_fixes:
            await execute_safely(conn, sql, desc)
        
        # 2. Fix user_sessions table structure
        logger.info("📋 Fixing user_sessions table...")
        
        # Check if session_id column exists
        session_id_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'user_sessions' AND column_name = 'session_id'
            )
        """)
        
        if not session_id_exists:
            # Drop and recreate user_sessions table with correct structure
            await execute_safely(conn, "DROP TABLE IF EXISTS user_sessions CASCADE;", "Dropped old user_sessions table")
            
            create_sessions_sql = """
                CREATE TABLE user_sessions (
                    session_id VARCHAR(128) PRIMARY KEY,
                    user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address INET,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT TRUE
                );
            """
            await execute_safely(conn, create_sessions_sql, "Created new user_sessions table")
        else:
            # Add missing columns if they don't exist
            session_fixes = [
                ("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP;", "Added last_activity column"),
                ("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS ip_address INET;", "Added ip_address column"),
                ("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS user_agent TEXT;", "Added user_agent column"),
                ("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;", "Added is_active column"),
            ]
            
            for sql, desc in session_fixes:
                await execute_safely(conn, sql, desc)
        
        # 3. Fix gst_search_history table
        logger.info("📋 Fixing gst_search_history table...")
        
        search_history_fixes = [
            ("ALTER TABLE gst_search_history ADD COLUMN IF NOT EXISTS mobile VARCHAR(15);", "Added mobile column"),
            ("ALTER TABLE gst_search_history ADD COLUMN IF NOT EXISTS company_name TEXT;", "Added company_name column"),
            ("ALTER TABLE gst_search_history ADD COLUMN IF NOT EXISTS compliance_score DECIMAL(5,2);", "Added compliance_score column"),
            ("ALTER TABLE gst_search_history ADD COLUMN IF NOT EXISTS ai_synopsis TEXT;", "Added ai_synopsis column"),
            ("ALTER TABLE gst_search_history ADD COLUMN IF NOT EXISTS searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;", "Added searched_at column"),
        ]
        
        for sql, desc in search_history_fixes:
            await execute_safely(conn, sql, desc)
        
        # 4. Create user_profiles table if it doesn't exist
        logger.info("📋 Creating/fixing user_profiles table...")
        
        create_profiles_sql = """
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
        """
        await execute_safely(conn, create_profiles_sql, "Created/verified user_profiles table")
        
        # 5. Create search_history table (alternative name that main.py might expect)
        logger.info("📋 Creating search_history table...")
        
        create_search_history_sql = """
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                gstin VARCHAR(15) NOT NULL,
                company_name TEXT,
                search_data JSONB,
                compliance_score DECIMAL(5,2),
                ai_synopsis TEXT,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        await execute_safely(conn, create_search_history_sql, "Created search_history table")
        
        # 6. Update mobile column data if user_mobile exists
        logger.info("📋 Updating data consistency...")
        
        # Check if user_mobile column exists in gst_search_history
        user_mobile_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'gst_search_history' AND column_name = 'user_mobile'
            )
        """)
        
        if user_mobile_exists:
            # Copy data from user_mobile to mobile if mobile is empty
            update_sql = """
                UPDATE gst_search_history 
                SET mobile = user_mobile 
                WHERE mobile IS NULL AND user_mobile IS NOT NULL;
            """
            await execute_safely(conn, update_sql, "Updated mobile column data")
        
        # 7. Create indexes (each in its own try-catch)
        logger.info("📋 Creating indexes...")
        
        indexes = [
            ("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);", "users email index"),
            ("CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);", "users is_active index"),
            ("CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login_attempt);", "users last_login index"),
            ("CREATE INDEX IF NOT EXISTS idx_sessions_user_mobile ON user_sessions(user_mobile);", "sessions user_mobile index"),
            ("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);", "sessions expires index"),
            ("CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON user_sessions(is_active);", "sessions is_active index"),
            ("CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON user_sessions(last_activity);", "sessions last_activity index"),
            ("CREATE INDEX IF NOT EXISTS idx_search_history_mobile ON search_history(mobile);", "search_history mobile index"),
            ("CREATE INDEX IF NOT EXISTS idx_search_history_gstin ON search_history(gstin);", "search_history gstin index"),
            ("CREATE INDEX IF NOT EXISTS idx_search_history_date ON search_history(searched_at);", "search_history date index"),
            ("CREATE INDEX IF NOT EXISTS idx_gst_search_mobile ON gst_search_history(mobile);", "gst_search_history mobile index"),
        ]
        
        for index_sql, desc in indexes:
            await execute_safely(conn, index_sql, desc)
        
        # 8. Create triggers
        logger.info("📋 Creating triggers...")
        
        # Create function
        function_sql = """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """
        await execute_safely(conn, function_sql, "Created updated_at function")
        
        # Apply triggers
        trigger_tables = ['users', 'user_profiles']
        for table in trigger_tables:
            drop_trigger_sql = f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};"
            create_trigger_sql = f"""
                CREATE TRIGGER update_{table}_updated_at
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """
            await execute_safely(conn, drop_trigger_sql, f"Dropped old {table} trigger")
            await execute_safely(conn, create_trigger_sql, f"Created {table} trigger")
        
        logger.info("✅ Database schema migration completed successfully!")
        
        # 9. Verify the migration
        logger.info("📋 Verifying migration...")
        
        # Check table structures
        tables = ['users', 'user_sessions', 'gst_search_history', 'user_profiles', 'search_history']
        for table in tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                logger.info(f"  ✅ Table {table}: {count} records")
            except Exception as e:
                logger.warning(f"  ⚠️ Table {table}: {e}")
        
        # Check specific columns
        session_id_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'user_sessions' AND column_name = 'session_id'
            )
        """)
        logger.info(f"  ✅ user_sessions.session_id column: {'EXISTS' if session_id_exists else 'MISSING'}")
        
        mobile_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'search_history' AND column_name = 'mobile'
            )
        """)
        logger.info(f"  ✅ search_history.mobile column: {'EXISTS' if mobile_exists else 'MISSING'}")
        
        logger.info("✅ Migration verification completed!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()

async def main():
    """Main function"""
    try:
        await fix_database_schema()
        print("\n" + "="*60)
        print("✅ Database schema migration completed successfully!")
        print("🎉 Your application should now work without schema errors!")
        print("="*60)
        return True
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)