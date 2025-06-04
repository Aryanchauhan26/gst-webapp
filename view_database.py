#!/usr/bin/env python3
"""
Database viewer script for GST Intelligence Platform
Run this to view your database contents
"""

import sqlite3
import os

def view_database():
    db_path = "database/gst_platform.db"
    if not os.path.exists(db_path):
        print("❌ Database not found. Run quick_db_fix.py first.")
        return

    with sqlite3.connect(db_path) as conn:
        print("\n--- Users ---")
        for row in conn.execute("SELECT mobile, created_at, last_login FROM users"):
            print(row)

        print("\n--- Recent Search History (up to 10 per user) ---")
        for row in conn.execute("SELECT mobile, gstin, company_name, searched_at, compliance_score FROM search_history ORDER BY searched_at DESC LIMIT 20"):
            print(row)

if __name__ == "__main__":
    view_database()