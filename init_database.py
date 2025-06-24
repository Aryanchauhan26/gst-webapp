#!/usr/bin/env python3
"""
Database initialization script for GST Intelligence Platform
Run this before starting the application for the first time
"""

import asyncio
import asyncpg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from config import settings
POSTGRES_DSN = settings.POSTGRES_DSN

async def create_error_logs_table(conn):
    """Create error logs table."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id SERIAL PRIMARY KEY,
            error_type VARCHAR(100),
            message TEXT,
            stack_trace TEXT,
            url TEXT,
            user_agent TEXT,
            user_mobile VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            additional_data JSONB,
            FOREIGN KEY (user_mobile) REFERENCES users(mobile) ON DELETE SET NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);
        CREATE INDEX IF NOT EXISTS idx_error_logs_user_mobile ON error_logs(user_mobile);
    """)
    logger.info("✅ Error logs table created/verified")

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
        
        # Create error logs table
        await create_error_logs_table(conn)
        
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