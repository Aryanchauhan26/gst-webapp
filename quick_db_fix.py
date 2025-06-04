#!/usr/bin/env python3
"""
Quick database fix - Run this to create the database immediately
"""

import os
import sqlite3

def quick_database_setup():
    """Quickly create the database structure"""
    
    print("🔧 Quick Database Setup for GST Intelligence Platform")
    print("=" * 50)
    
    # Database file path
    db_path = "database/gst_platform.db"
    
    # Create database and tables
    try:
        print(f"🔧 Creating database: {db_path}")
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        with sqlite3.connect(db_path) as conn:
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
            
            conn.commit()
            
        print("✅ Database created successfully!")
        print(f"📍 Full path: {db_path}")
        
        # Verify file was created
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
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
    db_path = "database/gst_platform.db"
    
    if not os.path.exists(db_path):
        print("❌ Database not found")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
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
    success = quick_database_setup()
    
    if success:
        print("\n" + "="*50)
        test_database()
        print("\n🎉 Database setup complete!")
        print("You can now run your main application.")
    else:
        print("\n❌ Database setup failed. Please check the errors above.")