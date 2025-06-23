#!/usr/bin/env python3
"""
Database viewer script for GST Intelligence Platform (PostgreSQL/Neon)
Run this to view your database contents
"""

import asyncio
import asyncpg

from config import settings
POSTGRES_DSN = settings.POSTGRES_DSN

async def view_database():
    try:
        conn = await asyncpg.connect(dsn=POSTGRES_DSN)
    except Exception as e:
        print(f"❌ Could not connect to database: {e}")
        return

    print("\n--- Users ---")
    rows = await conn.fetch("SELECT mobile, created_at, last_login FROM users")
    for row in rows:
        print(dict(row))

    print("\n--- Recent Search History (up to 20 entries) ---")
    rows = await conn.fetch(
        "SELECT mobile, gstin, company_name, searched_at, compliance_score FROM search_history ORDER BY searched_at DESC LIMIT 20"
    )
    for row in rows:
        print(dict(row))

    await conn.close()

if __name__ == "__main__":
    asyncio.run(view_database())