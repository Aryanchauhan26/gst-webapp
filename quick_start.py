#!/usr/bin/env python3
"""
GST Intelligence Platform - Quick Start Script
Run this to set up and start everything automatically
"""

import os
import sys
import subprocess
from pathlib import Path
import time

def print_banner():
    """Print application banner"""
    print("\n" + "="*60)
    print("🚀 GST INTELLIGENCE PLATFORM - QUICK START")
    print("="*60 + "\n")

def check_and_install_dependencies():
    """Check and install required packages"""
    print("📦 Checking dependencies...")
    
    try:
        import pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"])
        print("✅ Dependencies installed/verified")
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        print("Please run manually: pip install -r requirements.txt")
        return False
    return True

def setup_directories():
    """Create required directories"""
    print("\n📁 Setting up directories...")
    
    directories = ['static', 'templates', 'database']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Directories created/verified")
    return True

def setup_environment():
    """Set up environment variables"""
    print("\n🔧 Checking environment...")
    
    env_path = Path('.env')
    if not env_path.exists():
        print("📝 Creating .env file template...")
        with open(env_path, 'w') as f:
            f.write("# GST Intelligence Platform Configuration\n")
            f.write("RAPIDAPI_KEY=your_rapidapi_key_here\n")
            f.write("ANTHROPIC_API_KEY=your_anthropic_api_key_here\n")
            f.write("RAPIDAPI_HOST=gst-return-status.p.rapidapi.com\n")
        print("⚠️  Please edit .env file and add your API keys")
        print("   Get RapidAPI key from: https://rapidapi.com/")
        print("   Get Anthropic key from: https://www.anthropic.com/")
        return False
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv('RAPIDAPI_KEY') or os.getenv('RAPIDAPI_KEY') == 'your_rapidapi_key_here':
        print("⚠️  RAPIDAPI_KEY not set in .env file")
        return False
    
    print("✅ Environment configured")
    return True

def setup_database():
    """Initialize database"""
    print("\n💾 Setting up database...")
    
    try:
        import quick_db_fix
        quick_db_fix.quick_database_setup()
        return True
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def check_dark_theme():
    """Check if dark theme CSS exists"""
    print("\n🎨 Checking dark theme...")
    
    css_path = Path("static/style.css")
    if not css_path.exists():
        print("❌ Dark theme CSS not found at static/style.css")
        print("⚠️  Please save the dark theme CSS file to static/style.css")
        print("   The dark theme provides the beautiful dark UI styling")
        return False
    
    print("✅ Dark theme CSS found")
    return True

def start_application():
    """Start the FastAPI application"""
    print("\n🌐 Starting application...")
    print("-" * 60)
    print("📍 Main Application: http://localhost:8000")
    print("📍 API Documentation: http://localhost:8000/docs")
    print("📍 Database Viewer: Run 'python db_web_viewer.py' in another terminal")
    print("-" * 60)
    print("Press Ctrl+C to stop the server\n")
    
    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"])
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

def main():
    """Main quick start function"""
    print_banner()
    
    # Run all setup steps
    steps = [
        ("Dependencies", check_and_install_dependencies),
        ("Directories", setup_directories),
        ("Database", setup_database),
        ("Dark Theme", check_dark_theme),
        ("Environment", setup_environment),
    ]
    
    all_passed = True
    for step_name, step_func in steps:
        if not step_func():
            all_passed = False
            print(f"\n⚠️  {step_name} setup needs attention")
    
    if not all_passed:
        print("\n" + "="*60)
        print("❌ Some setup steps need attention. Please fix the issues above.")
        print("="*60)
        
        if not Path('.env').exists() or not os.getenv('RAPIDAPI_KEY'):
            print("\n📝 Next steps:")
            print("1. Edit the .env file and add your API keys")
            print("2. Run this script again: python quick_start.py")
        
        if not Path("static/style.css").exists():
            print("\n📝 Next steps:")
            print("1. Save the dark theme CSS to static/style.css")
            print("2. Run this script again: python quick_start.py")
        
        return
    
    print("\n" + "="*60)
    print("✅ All setup complete! Starting application...")
    print("="*60)
    
    # Add a small delay for user to read the messages
    time.sleep(2)
    
    # Start the application
    start_application()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check the error and try again")