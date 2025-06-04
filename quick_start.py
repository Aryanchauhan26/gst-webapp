#!/usr/bin/env python3
"""
Quick start script for GST Intelligence Platform.
Installs dependencies, sets up the database, and runs the app.
"""

import subprocess
import sys
import os

def install_requirements():
    print("🔧 Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def setup_database():
    print("🔧 Setting up the database...")
    subprocess.check_call([sys.executable, "quick_db_fix.py"])

def run_app():
    print("🚀 Starting the app...")
    subprocess.check_call([sys.executable, "-m", "uvicorn", "main:app", "--reload"])

def main():
    install_requirements()
    setup_database()
    run_app()

if __name__ == "__main__":
    main()