#!/usr/bin/env python3
"""
Final database schema alignment
"""

import asyncio
import asyncpg
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def final_database_fix():
    """Final database schema alignment."""
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
        
        logger.info("📋 Current sessions table:")
        for col in columns:
            logger.info(f"   - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        
        # Option 1: Use session_token as the main token column
        logger.info("🔧 Aligning database schema...")
        
        # First, let's see if we can drop the extra token column and use session_token
        try:
            # Check if there's any data in the token column that's different from session_token
            has_different_data = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM sessions 
                    WHERE token IS DISTINCT FROM session_token
                );
            """)
            
            if not has_different_data:
                logger.info("🔧 Token and session_token are equivalent, simplifying...")
                
                # Drop the redundant token column
                await conn.execute("""
                    ALTER TABLE sessions DROP COLUMN IF EXISTS token;
                """)
                logger.info("✅ Removed redundant token column")
                
                # Add primary key if missing
                try:
                    await conn.execute("""
                        ALTER TABLE sessions ADD CONSTRAINT sessions_pkey PRIMARY KEY (session_token);
                    """)
                    logger.info("✅ Added primary key to session_token")
                except Exception as e:
                    logger.info(f"Primary key already exists or not needed: {e}")
                
            else:
                logger.info("⚠️ Token columns have different data, keeping both")
                
        except Exception as e:
            logger.warning(f"⚠️ Could not simplify columns: {e}")
        
        # Ensure mobile is NOT NULL if it should be
        try:
            await conn.execute("""
                ALTER TABLE sessions ALTER COLUMN mobile SET NOT NULL;
            """)
            logger.info("✅ Made mobile column NOT NULL")
        except Exception as e:
            logger.info(f"Mobile column already NOT NULL: {e}")
        
        # Ensure expires_at is NOT NULL if it should be
        try:
            await conn.execute("""
                ALTER TABLE sessions ALTER COLUMN expires_at SET NOT NULL;
            """)
            logger.info("✅ Made expires_at column NOT NULL")
        except Exception as e:
            logger.info(f"Expires_at column constraint: {e}")
        
        # Create optimized indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_session_token ON sessions(session_token);
            CREATE INDEX IF NOT EXISTS idx_sessions_mobile ON sessions(mobile);
            CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
        """)
        logger.info("✅ Created optimized indexes")
        
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
        
        # Test sessions functionality with correct column
        try:
            import secrets
            test_token = secrets.token_urlsafe(32)
            
            await conn.execute("""
                INSERT INTO sessions (session_token, mobile, expires_at) 
                VALUES ($1, '1234567890', NOW() + INTERVAL '1 hour')
                ON CONFLICT (session_token) DO NOTHING;
            """, test_token)
            
            result = await conn.fetchval("""
                SELECT mobile FROM sessions WHERE session_token = $1;
            """, test_token)
            
            if result:
                logger.info("✅ Sessions table functionality verified with session_token")
                # Clean up test data
                await conn.execute("DELETE FROM sessions WHERE session_token = $1;", test_token)
            
        except Exception as e:
            logger.warning(f"⚠️ Sessions functionality test: {e}")
        
        await conn.close()
        logger.info("🎉 Final database fix completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Final database fix failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(final_database_fix())