#!/usr/bin/env python3
"""
Quick database fix - Run this to create the database immediately
"""

import os
import sqlite3
from pathlib import Path

def quick_database_setup():
    """Quickly create the database structure"""
    
    print("🔧 Quick Database Setup for GST Intelligence Platform")
    print("=" * 50)
    
    # Create database directory
    db_dir = Path("database")
    if not db_dir.exists():
        db_dir.mkdir()
        print(f"📁 Created directory: {db_dir}")
    else:
        print(f"📁 Directory exists: {db_dir}")
    
    # Database file path
    db_path = db_dir / "gst_platform.db"
    
    # Create database and tables
    try:
        print(f"🔧 Creating database: {db_path}")
        
        with sqlite3.connect(str(db_path)) as conn:
            # Users table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    mobile TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_login TEXT
                )
            ''')
            
            # Sessions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token TEXT PRIMARY KEY,
                    mobile TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT NOT NULL
                )
            ''')
            
            # Search history table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mobile TEXT NOT NULL,
                    gstin TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    searched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    compliance_score REAL
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_mobile ON sessions(mobile)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_history_mobile ON search_history(mobile)')
            
            conn.commit()
            
        print("✅ Database created successfully!")
        print(f"📍 Full path: {db_path.absolute()}")
        
        # Verify file was created
        if db_path.exists():
            size = db_path.stat().st_size
            print(f"📊 File size: {size} bytes")
            print("✅ Database file verified!")
            return True
        else:
            print("❌ Database file was not created")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_database():
    """Test database connection"""
    db_path = Path("database/gst_platform.db")
    
    if not db_path.exists():
        print("❌ Database not found")
        return False
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"✅ Database connection successful")
            print(f"📋 Tables found: {tables}")
            
            expected_tables = ['users', 'sessions', 'search_history']
            missing_tables = [t for t in expected_tables if t not in tables]
            
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
    print("Current directory:", os.getcwd())
    print("Files in current directory:", os.listdir("."))
    
    success = quick_database_setup()
    
    if success:
        print("\n" + "="*50)
        test_database()
        print("\n🎉 Database setup complete!")
        print("You can now run your main application.")
    else:
        print("\n❌ Database setup failed. Please check the errors above.")