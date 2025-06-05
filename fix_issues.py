#!/usr/bin/env python3
"""
Diagnostic script for GST Intelligence Platform.
Checks Python version, dependencies, and database presence.
"""

import sys
import os
import asyncio

POSTGRES_DSN = "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

def check_python():
    print(f"Python version: {sys.version}")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required.")
        return False
    print("✅ Python version OK.")
    return True

def check_requirements():
    try:
        import fastapi, uvicorn, lxml, asyncpg
        print("✅ Required packages are installed.")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e.name}")
        return False

async def check_database():
    try:
        import asyncpg
        conn = await asyncpg.connect(dsn=POSTGRES_DSN)
        await conn.execute("SELECT 1")
        await conn.close()
        print("✅ Connected to Neon/PostgreSQL database.")
        return True
    except Exception as e:
        print(f"❌ Could not connect to Neon/PostgreSQL: {e}")
        return False

def main():
    print("GST Intelligence Platform - Diagnostic Check")
    print("=" * 50)
    ok = check_python() and check_requirements()
    db_ok = asyncio.run(check_database())
    if ok and db_ok:
        print("✅ All checks passed.")
    else:
        print("❌ Some checks failed. Please fix the issues above.")

if __name__ == "__main__":
    main()