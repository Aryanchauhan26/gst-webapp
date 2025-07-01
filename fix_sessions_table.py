#!/usr/bin/env python3
"""
Fix sessions table schema - Add missing updated_at column
"""

import asyncio
import asyncpg
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_sessions_table():
    """Add missing updated_at and created_at columns to sessions table."""
    try:
        dsn = os.getenv('POSTGRES_DSN')
        conn = await asyncpg.connect(dsn)
        logger.info("✅ Connected to database")
        
        # Check current sessions table structure
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'sessions'
            ORDER BY ordinal_position;
        """)
        
        logger.info("📋 Current sessions table structure:")
        for col in columns:
            logger.info(f"   - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        
        # Check if created_at column exists and add if missing
        created_at_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'sessions' AND column_name = 'created_at'
            );
        """)
        
        if not created_at_exists:
            logger.info("🔧 Adding missing created_at column...")
            await conn.execute("""
                ALTER TABLE sessions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)
            logger.info("✅ Added created_at column to sessions table")
        else:
            logger.info("✅ created_at column already exists")
        
        # Check if updated_at column exists
        updated_at_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'sessions' AND column_name = 'updated_at'
            );
        """)
        
        if not updated_at_exists:
            logger.info("🔧 Adding missing updated_at column...")
            await conn.execute("""
                ALTER TABLE sessions ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)
            logger.info("✅ Added updated_at column to sessions table")
        else:
            logger.info("✅ updated_at column already exists")
        
        # Update existing records to have proper timestamps
        logger.info("🔧 Updating existing sessions with proper timestamps...")
        await conn.execute("""
            UPDATE sessions 
            SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP),
                updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)
            WHERE created_at IS NULL OR updated_at IS NULL;
        """)
        logger.info("✅ Updated existing sessions with timestamp values")
        
        # Final verification
        final_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'sessions'
            ORDER BY ordinal_position;
        """)
        
        logger.info("📋 Final sessions table structure:")
        for col in final_columns:
            logger.info(f"   - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        
        # Test session creation
        try:
            import secrets
            from datetime import datetime, timedelta
            
            test_token = secrets.token_urlsafe(32)
            test_mobile = "0000000000"  # Test mobile
            expires_at = datetime.now() + timedelta(hours=1)
            
            await conn.execute("""
                INSERT INTO sessions (session_token, mobile, expires_at, created_at, updated_at) 
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (session_token) DO NOTHING;
            """, test_token, test_mobile, expires_at)
            
            logger.info("✅ Sessions table functionality test passed")
            
            # Clean up test data
            await conn.execute("DELETE FROM sessions WHERE mobile = $1;", test_mobile)
            logger.info("✅ Test cleanup completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Sessions functionality test failed: {e}")
        
        await conn.close()
        logger.info("🎉 Sessions table fix completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Sessions table fix failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_sessions_table())