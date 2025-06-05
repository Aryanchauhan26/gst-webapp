#!/usr/bin/env python3
"""
Quick database fix - Run this to create the PostgreSQL/Neon database tables immediately
"""

import asyncio
import asyncpg

POSTGRES_DSN = "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        mobile VARCHAR(20) PRIMARY KEY,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        session_token TEXT PRIMARY KEY,
        mobile VARCHAR(20) REFERENCES users(mobile),
        expires_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS search_history (
        id SERIAL PRIMARY KEY,
        mobile VARCHAR(20) REFERENCES users(mobile),
        gstin VARCHAR(20),
        company_name TEXT,
        compliance_score FLOAT,
        searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
]

async def quick_database_setup():
    print("🔧 Quick Database Setup for GST Intelligence Platform (PostgreSQL/Neon)")
    print("=" * 50)
    try:
        conn = await asyncpg.connect(dsn=POSTGRES_DSN)
        for sql in CREATE_TABLES_SQL:
            await conn.execute(sql)
        await conn.close()
        print("✅ Tables created successfully in Neon/PostgreSQL!")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_database():
    try:
        conn = await asyncpg.connect(dsn=POSTGRES_DSN)
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )
        table_names = [row['table_name'] for row in tables]
        print(f"✅ Database connection successful")
        print(f"📋 Tables found: {table_names}")
        expected_tables = ['users', 'sessions', 'search_history']
        missing_tables = [t for t in expected_tables if t not in table_names]
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        else:
            print("✅ All required tables present")
            return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_database_setup())
    if success:
        print("\n" + "="*50)
        asyncio.run(test_database())
        print("\n🎉 Database setup complete!")
        print("You can now run your main application.")
    else:
        print("\n❌ Database setup failed. Please check the errors above.")