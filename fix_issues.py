#!/usr/bin/env python3
"""
Diagnostic script for GST Intelligence Platform.
Checks Python version, dependencies, and database presence.
"""

import sys
import os

def check_python():
    print(f"Python version: {sys.version}")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required.")
        return False
    print("✅ Python version OK.")
    return True

def check_requirements():
    try:
        import fastapi, uvicorn, lxml
        print("✅ Required packages are installed.")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e.name}")
        return False

def check_database():
    db_path = "database/gst_platform.db"
    if os.path.exists(db_path):
        print(f"✅ Database found at {db_path}")
        return True
    else:
        print(f"❌ Database not found at {db_path}")
        return False

def main():
    print("GST Intelligence Platform - Diagnostic Check")
    print("=" * 50)
    ok = check_python() and check_requirements() and check_database()
    if ok:
        print("✅ All checks passed.")
    else:
        print("❌ Some checks failed. Please fix the issues above.")

if __name__ == "__main__":
    main()