#!/usr/bin/env python3
"""
Migration script for GST Intelligence Platform.
Use this to migrate old user/search data to the new PostgreSQL/Neon database.
"""

import os
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
import sys
import asyncio
import asyncpg

POSTGRES_DSN = "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

def generate_salt():
    """Generate a random salt for password hashing"""
    return secrets.token_hex(16)

def hash_password_pbkdf2(password: str, salt: str) -> str:
    """Hash password with salt using PBKDF2"""
    password_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    hash_bytes = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, 100000, dklen=64)
    return hash_bytes.hex()

async def migrate_data():
    """Migrate data from JSON files to PostgreSQL/Neon database"""
    db_dir = Path("database")
    users_file = db_dir / "users.json"
    history_file = db_dir / "history.json"
    sessions_file = db_dir / "sessions.json"

    if not any(f.exists() for f in [users_file, history_file, sessions_file]):
        print("No existing JSON files found. Starting with fresh PostgreSQL database.")
        return

    try:
        conn = await asyncpg.connect(dsn=POSTGRES_DSN)
    except Exception as e:
        print(f"❌ Could not connect to PostgreSQL: {e}")
        return

    # Migrate users
    if users_file.exists():
        try:
            with open(users_file, 'r') as f:
                users_data = json.load(f)
            migrated_users = 0
            for mobile, user_data in users_data.items():
                try:
                    old_hash = user_data.get('password_hash', '')
                    salt = generate_salt()
                    new_hash = hash_password_pbkdf2(old_hash, salt)
                    created_at = user_data.get('created_at')
                    last_login = user_data.get('last_login')
                    await conn.execute('''
                        INSERT INTO users (mobile, password_hash, salt, created_at, last_login)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (mobile) DO UPDATE SET password_hash=EXCLUDED.password_hash, salt=EXCLUDED.salt, created_at=EXCLUDED.created_at, last_login=EXCLUDED.last_login
                    ''', mobile, new_hash, salt, created_at, last_login)
                    migrated_users += 1
                except Exception as e:
                    print(f"Error migrating user {mobile}: {e}")
            print(f"Migrated {migrated_users} users")
            backup_path = users_file.with_suffix('.json.backup')
            users_file.rename(backup_path)
            print(f"Backed up users.json to {backup_path}")
        except Exception as e:
            print(f"Error migrating users: {e}")

    # Migrate sessions (skipped)
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
                        await conn.execute('''
                            INSERT INTO search_history (mobile, gstin, company_name, searched_at, compliance_score)
                            VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT (mobile, gstin) DO UPDATE SET company_name=EXCLUDED.company_name, searched_at=EXCLUDED.searched_at, compliance_score=EXCLUDED.compliance_score
                        ''', mobile, gstin, company_name, searched_at, compliance_score)
                        migrated_history += 1
                    except Exception as e:
                        print(f"Error migrating search history for {mobile}: {e}")
            print(f"Migrated {migrated_history} search history entries")
            backup_path = history_file.with_suffix('.json.backup')
            history_file.rename(backup_path)
            print(f"Backed up history.json to {backup_path}")
        except Exception as e:
            print(f"Error migrating search history: {e}")

    await conn.close()
    print("\n" + "="*50)
    print("MIGRATION COMPLETE")
    print("="*50)
    print("IMPORTANT: Due to security improvements, all users will need to:")
    print("1. Reset their passwords using the 'Forgot Password' feature (if implemented)")
    print("2. Or re-register their accounts")
    print("3. The old password hashes cannot be directly converted to the new secure format")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(migrate_data())