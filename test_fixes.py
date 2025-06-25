#!/usr/bin/env python3
"""
Test script for verifying critical fixes
Run this after applying the fixes to main.py
"""

import asyncio
import sys

def test_imports():
    """Test if all imports work"""
    try:
        from main import app, db, cache_manager, RateLimiter
        print("✅ All imports working")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

async def test_database():
    """Test database connection"""
    try:
        from config import settings
        import asyncpg
        
        conn = await asyncpg.connect(settings.POSTGRES_DSN)
        await conn.execute('SELECT 1')
        await conn.close()
        print("✅ Database connection working")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

async def test_cache_manager():
    """Test cache manager"""
    try:
        from main import cache_manager
        
        # Test basic operations
        await cache_manager.set('test_key', 'test_value')
        value = await cache_manager.get('test_key')
        
        if value == 'test_value':
            print("✅ Cache manager working")
        else:
            print("❌ Cache manager not storing/retrieving correctly")
            return False
            
        # Test cleanup
        await cache_manager.close()
        print("✅ Cache manager cleanup working")
        return True
    except Exception as e:
        print(f"❌ Cache manager error: {e}")
        return False

def test_rate_limiter():
    """Test rate limiter"""
    try:
        from main import RateLimiter
        
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # Test normal operation
        for i in range(3):
            if not limiter.is_allowed(f'test_user_{i}'):
                print("❌ Rate limiter blocking too early")
                return False
        
        print("✅ Rate limiter working")
        return True
    except Exception as e:
        print(f"❌ Rate limiter error: {e}")
        return False

async def test_database_initialization():
    """Test database initialization"""
    try:
        from main import db
        
        await db.initialize()
        print("✅ Database initialization working")
        return True
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🔍 Testing critical fixes...")
    print("=" * 50)
    
    # Test imports first
    if not test_imports():
        print("❌ Cannot continue - imports failed")
        sys.exit(1)
    
    # Test components
    tests = [
        ("Database Connection", test_database()),
        ("Database Initialization", test_database_initialization()),
        ("Cache Manager", test_cache_manager()),
        ("Rate Limiter", test_rate_limiter())
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_coro in tests:
        print(f"\n🧪 Testing {test_name}...")
        try:
            if asyncio.iscoroutine(test_coro):
                result = await test_coro
            else:
                result = test_coro
            
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All critical fixes working correctly!")
        print("✅ Your application is ready to run")
    else:
        print("⚠️  Some tests failed - please check the errors above")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())