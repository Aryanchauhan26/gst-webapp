#!/usr/bin/env python3
"""
Startup script for GST Intelligence Platform
Handles database initialization and migration
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ['RAPIDAPI_KEY', 'ANTHROPIC_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these environment variables before starting the application.")
        print("You can create a .env file with the following format:")
        print()
        for var in missing_vars:
            print(f"{var}=your_api_key_here")
        print()
        return False
    
    print("✅ Environment variables are properly configured")
    return True

def check_database():
    """Check if database exists and is properly initialized"""
    db_path = Path("database") / "gst_platform.db"
    
    if not db_path.exists():
        print("🔄 Database not found. Initializing new SQLite database...")
        # Import and create database
        try:
            from main import SQLiteDB
            db = SQLiteDB()
            print("✅ Database initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize database: {e}")
            return False
    else:
        print("✅ Database found and ready")
        return True

def check_dependencies():
    """Check if all required packages are installed"""
    try:
        import fastapi
        import uvicorn
        import httpx
        import weasyprint
        import anthropic
        import beautifulsoup4
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please install required packages:")
        print("pip install -r requirements.txt")
        return False

def run_migration_if_needed():
    """Run migration from JSON to SQLite if old files exist"""
    json_files = [
        Path("database") / "users.json",
        Path("database") / "history.json", 
        Path("database") / "sessions.json"
    ]
    
    if any(f.exists() for f in json_files):
        print("🔄 Old JSON database files detected. Running migration...")
        try:
            import migration
            migration.migrate_data()
            print("✅ Migration completed successfully")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            print("You may need to run migration.py manually")
            return False
    
    return True

def main():
    """Main startup routine"""
    print("🚀 Starting GST Intelligence Platform")
    print("=" * 50)
    
    # Check all prerequisites
    checks = [
        ("Environment Variables", check_environment),
        ("Dependencies", check_dependencies),
        ("Database Migration", run_migration_if_needed),
        ("Database", check_database),
    ]
    
    for check_name, check_func in checks:
        print(f"\n📋 Checking {check_name}...")
        if not check_func():
            print(f"\n❌ Startup failed at: {check_name}")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ All checks passed! Starting the application...")
    print("=" * 50)
    
    # Start the application
    try:
        import uvicorn
        from main import app
        
        print("\n🌐 Application starting at: http://localhost:8000")
        print("📊 Admin interface at: http://localhost:8000/docs")
        print("\n💡 Press Ctrl+C to stop the server")
        print("-" * 50)
        
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            reload=False,  # Set to True for development
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()