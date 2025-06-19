# Location: create_user_prefs.py (NEW FILE)
import asyncio
import asyncpg

POSTGRES_DSN = "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

async def create_user_preferences_table():
    """Create user preferences table"""
    conn = await asyncpg.connect(dsn=POSTGRES_DSN)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                mobile VARCHAR(10) PRIMARY KEY,
                preferences JSONB NOT NULL DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_user_preferences_mobile ON user_preferences(mobile);
        """)
        print("✅ User preferences table created successfully")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_user_preferences_table())