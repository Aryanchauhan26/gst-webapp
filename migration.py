#!/usr/bin/env python3
"""
Migration script for GST Intelligence Platform.
Use this to migrate old user/search data to the new SQLite database.
"""

import os
import sqlite3
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
import sys

def generate_salt():
    """Generate a random salt for password hashing"""
    return secrets.token_hex(16)

def hash_password_pbkdf2(password: str, salt: str) -> str:
    """Hash password with salt using PBKDF2"""
    # FIXED: Use the correct function pbkdf2_hmac
    password_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    
    # PBKDF2 with SHA256, 100000 iterations, 64 bytes output
    hash_bytes = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, 100000, dklen=64)
    
    # Convert to hex string
    return hash_bytes.hex()

def migrate_data():
    """Migrate data from JSON files to SQLite database"""
    
    # Check if old JSON files exist
    db_dir = Path("database")
    users_file = db_dir / "users.json"
    history_file = db_dir / "history.json"
    sessions_file = db_dir / "sessions.json"
    
    if not any(f.exists() for f in [users_file, history_file, sessions_file]):
        print("No existing JSON files found. Starting with fresh SQLite database.")
        return
    
    # Create SQLite database
    db_path = db_dir / "gst_platform.db"
    
    print(f"Creating SQLite database at {db_path}")
    
    with sqlite3.connect(db_path) as conn:
        # Create tables
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                mobile TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_token TEXT PRIMARY KEY,
                mobile TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (mobile) REFERENCES users (mobile) ON DELETE CASCADE
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mobile TEXT NOT NULL,
                gstin TEXT NOT NULL,
                company_name TEXT NOT NULL,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                compliance_score REAL,
                FOREIGN KEY (mobile) REFERENCES users (mobile) ON DELETE CASCADE,
                UNIQUE(mobile, gstin)
            )
        ''')
        
        # Create indexes
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_mobile ON sessions(mobile)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_history_mobile ON search_history(mobile)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_history_searched_at ON search_history(searched_at DESC)')
        
        conn.commit()
        print("Created database tables and indexes")
        
        # Migrate users
        if users_file.exists():
            try:
                with open(users_file, 'r') as f:
                    users_data = json.load(f)
                
                migrated_users = 0
                for mobile, user_data in users_data.items():
                    try:
                        # Generate new salt and re-hash password
                        # Note: We can't recover the original password, so we'll use the old hash as a temporary password
                        # Users will need to reset their passwords or we could prompt them to re-enter
                        old_hash = user_data.get('password_hash', '')
                        
                        # For migration, we'll create a new salt and hash the old hash
                        # This is not ideal, but necessary since we can't recover original passwords
                        salt = generate_salt()
                        new_hash = hash_password_pbkdf2(old_hash, salt)
                        
                        created_at = user_data.get('created_at')
                        last_login = user_data.get('last_login')
                        
                        conn.execute('''
                            INSERT OR REPLACE INTO users (mobile, password_hash, salt, created_at, last_login)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (mobile, new_hash, salt, created_at, last_login))
                        
                        migrated_users += 1
                    except Exception as e:
                        print(f"Error migrating user {mobile}: {e}")
                
                conn.commit()
                print(f"Migrated {migrated_users} users")
                
                # Backup and remove old file
                backup_path = users_file.with_suffix('.json.backup')
                users_file.rename(backup_path)
                print(f"Backed up users.json to {backup_path}")
                
            except Exception as e:
                print(f"Error migrating users: {e}")
        
        # Migrate sessions (most will be expired anyway, so we'll skip this)
        if sessions_file.exists():
            print("Skipping session migration (sessions will be recreated on login)")
            backup_path = sessions_file.with_suffix('.json.backup')
            sessions_file.rename(backup_path)
            print(f"Backed up sessions.json to {backup_path}")
        
        # Migrate search history
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                
                migrated_history = 0
                for mobile, searches in history_data.items():
                    for search in searches:
                        try:
                            gstin = search.get('gstin')
                            company_name = search.get('company_name')
                            searched_at = search.get('searched_at')
                            compliance_score = search.get('compliance_score')
                            
                            conn.execute('''
                                INSERT OR REPLACE INTO search_history 
                                (mobile, gstin, company_name, searched_at, compliance_score)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (mobile, gstin, company_name, searched_at, compliance_score))
                            
                            migrated_history += 1
                        except Exception as e:
                            print(f"Error migrating search history for {mobile}: {e}")
                
                conn.commit()
                print(f"Migrated {migrated_history} search history entries")
                
                # Backup and remove old file
                backup_path = history_file.with_suffix('.json.backup')
                history_file.rename(backup_path)
                print(f"Backed up history.json to {backup_path}")
                
            except Exception as e:
                print(f"Error migrating search history: {e}")
    
    print("\n" + "="*50)
    print("MIGRATION COMPLETE")
    print("="*50)
    print("IMPORTANT: Due to security improvements, all users will need to:")
    print("1. Reset their passwords using the 'Forgot Password' feature (if implemented)")
    print("2. Or re-register their accounts")
    print("3. The old password hashes cannot be directly converted to the new secure format")
    print("\nAlternatively, you can temporarily set a known password for testing:")
    print("Run this script with --set-test-passwords to set all passwords to 'test123'")
    print("="*50)

def set_test_passwords():
    """Set all user passwords to 'test123' for easier testing"""
    db_path = Path("database") / "gst_platform.db"
    
    if not db_path.exists():
        print("SQLite database not found. Run migration first.")
        return
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute('SELECT mobile FROM users')
        users = cursor.fetchall()
        
        updated = 0
        for (mobile,) in users:
            salt = generate_salt()
            password_hash = hash_password_pbkdf2('test123', salt)
            
            conn.execute('''
                UPDATE users SET password_hash = ?, salt = ? WHERE mobile = ?
            ''', (password_hash, salt, mobile))
            updated += 1
        
        conn.commit()
        print(f"Updated {updated} user passwords to 'test123'")

def migrate():
    db_path = "database/gst_platform.db"
    if not os.path.exists(db_path):
        print("❌ Database not found. Run quick_db_fix.py first.")
        return

    # Example: Migrate from old JSON/CSV (customize as needed)
    # old_data = load_old_data("old_data.json")  # Implement this if needed

    # Example migration logic (replace with your actual migration)
    # for user in old_data["users"]:
    #     with sqlite3.connect(db_path) as conn:
    #         conn.execute(
    #             "INSERT OR IGNORE INTO users (mobile, password_hash, salt) VALUES (?, ?, ?)",
    #             (user["mobile"], user["password_hash"], user["salt"])
    #         )
    #         conn.commit()
    print("✅ Migration script ran (customize this for your actual data).")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--set-test-passwords":
        set_test_passwords()
    else:
        migrate_data()
        migrate()