#!/usr/bin/env python3
"""
Production start script for GST Intelligence Platform.
Checks environment and launches the app.
"""

import os
import sys
import subprocess

def check_env():
    required = ["RAPIDAPI_KEY"]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    print("✅ Environment variables OK.")

def run_app():
    print("🚀 Starting the app (production mode)...")
    subprocess.check_call([sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"])

def main():
    check_env()
    run_app()

if __name__ == "__main__":
    main()