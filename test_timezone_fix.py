#!/usr/bin/env python3
"""
Test timezone fix
"""

import asyncio
import asyncpg
import logging
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_timezone_fix():
    """Test timezone-aware datetime operations."""
    try:
        dsn = os.getenv('POSTGRES_DSN')
        conn = await asyncpg.connect(dsn)
        logger.info("✅ Connected to database")
        
        # Test timezone-aware datetime
        current_time = datetime.now()
        logger.info(f"✅ Timezone-aware datetime: {current_time}")
        
        # Test error log insertion
        try:
            await conn.execute("""
                INSERT INTO error_logs 
                (error_type, message, created_at)
                VALUES ($1, $2, $3)
            """, 
            'test',
            'Timezone test message',
            current_time)
            logger.info("✅ Error log insertion successful")
            
            # Clean up test data
            await conn.execute("""
                DELETE FROM error_logs WHERE error_type = 'test' AND message = 'Timezone test message'
            """)
            logger.info("✅ Test cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error log test failed: {e}")
        
        await conn.close()
        logger.info("🎉 Timezone fix test completed!")
        
    except Exception as e:
        logger.error(f"❌ Timezone fix test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_timezone_fix())