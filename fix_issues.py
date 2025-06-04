#!/usr/bin/env python3
"""
GST Intelligence Platform - Diagnostic and Fix Script
This script will diagnose and fix common issues
"""

import os
import sys
from pathlib import Path
import subprocess
import sqlite3

def print_header(text):
    print("\n" + "="*60)
    print(f"🔧 {text}")
    print("="*60)

def check_python_version():
    """Check if Python version is compatible"""
    print_header("Checking Python Version")
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    print("✅ Python version is compatible")
    return True

def check_environment_variables():
    """Check if required environment variables are set"""
    print_header("Checking Environment Variables")
    
    required_vars = {
        'RAPIDAPI_KEY': 'Required for GST data fetching',
        'ANTHROPIC_API_KEY': 'Optional but recommended for AI summaries'
    }
    
    missing = []
    for var, description in required_vars.items():
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} is missing - {description}")
            if var == 'RAPIDAPI_KEY':
                missing.append(var)
    
    if missing:
        print("\n📝 To fix missing environment variables:")
        print("1. Create a .env file in the project root")
        print("2. Add the following lines:")
        for var in missing:
            print(f"   {var}=your_api_key_here")
        return False
    
    return True

def check_dependencies():
    """Check if all required packages are installed"""
    print_header("Checking Dependencies")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'httpx',
        'weasyprint',
        'anthropic',
        'beautifulsoup4',
        'googlesearch-python',
        'python-dotenv',
        'jinja2',
        'python-multipart'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is missing")
            missing.append(package)
    
    if missing:
        print("\n📝 To install missing packages:")
        print("   pip install -r requirements.txt")
        print("\nOr install individually:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True

def check_directory_structure():
    """Check and create required directories"""
    print_header("Checking Directory Structure")
    
    directories = ['static', 'templates', 'database']
    
    for directory in directories:
        path = Path(directory)
        if path.exists():
            print(f"✅ {directory}/ exists")
        else:
            path.mkdir(exist_ok=True)
            print(f"📁 Created {directory}/ directory")
    
    return True

def check_css_files():
    """Check if CSS files exist"""
    print_header("Checking CSS Files")
    
    css_files = {
        'static/style.css': 'Main dark theme styles',
        'static/common-styles.css': 'Common styles (optional)'
    }
    
    for file_path, description in css_files.items():
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            print(f"✅ {file_path} exists ({size} bytes) - {description}")
        else:
            print(f"❌ {file_path} is missing - {description}")
            print("   The dark theme CSS has been created. Save it to this location.")
    
    return True

def check_database():
    """Check if database exists and is properly initialized"""
    print_header("Checking Database")
    
    db_path = Path("database/gst_platform.db")
    
    if db_path.exists():
        print(f"✅ Database exists at {db_path}")
        
        # Check tables
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                required_tables = ['users', 'sessions', 'search_history']
                for table in required_tables:
                    if table in tables:
                        print(f"   ✅ Table '{table}' exists")
                    else:
                        print(f"   ❌ Table '{table}' is missing")
                        return False
                        
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            return False
    else:
        print("❌ Database does not exist")
        print("\n📝 To create the database:")
        print("   python quick_db_fix.py")
        return False
    
    return True

def check_templates():
    """Check if all required templates exist"""
    print_header("Checking Templates")
    
    templates = [
        'index.html',
        'login.html',
        'signup.html',
        'history.html',
        'change_password.html',
        'pdf_template.html'
    ]
    
    for template in templates:
        path = Path(f"templates/{template}")
        if path.exists():
            print(f"✅ {template} exists")
        else:
            print(f"❌ {template} is missing")
    
    return True

def test_imports():
    """Test importing the main application"""
    print_header("Testing Application Import")
    
    try:
        from main import app
        print("✅ Successfully imported FastAPI app")
        return True
    except Exception as e:
        print(f"❌ Failed to import app: {e}")
        return False

def run_diagnostics():
    """Run all diagnostic checks"""
    print("\n🏥 GST Intelligence Platform - Diagnostic Tool")
    print("This will check your installation and fix common issues\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Directory Structure", check_directory_structure),
        ("Dependencies", check_dependencies),
        ("CSS Files", check_css_files),
        ("Database", check_database),
        ("Templates", check_templates),
        ("Environment Variables", check_environment_variables),
        ("Application Import", test_imports)
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ Error during {name} check: {e}")
            results[name] = False
    
    # Summary
    print_header("Diagnostic Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"Checks passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All checks passed! Your application should be ready to run.")
        print("\nTo start the application:")
        print("   python main.py")
        print("\nOr use uvicorn directly:")
        print("   uvicorn main:app --reload")
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        
        # Provide quick fixes
        print("\n🛠️  Quick Fix Commands:")
        
        if not results.get("Dependencies"):
            print("\n1. Install dependencies:")
            print("   pip install -r requirements.txt")
        
        if not results.get("Database"):
            print("\n2. Create database:")
            print("   python quick_db_fix.py")
        
        if not results.get("Environment Variables"):
            print("\n3. Create .env file with your API keys")
        
        if not results.get("CSS Files"):
            print("\n4. Save the dark theme CSS to static/style.css")

def fix_common_issues():
    """Attempt to fix common issues automatically"""
    print_header("Attempting Automatic Fixes")
    
    # Create directories
    for directory in ['static', 'templates', 'database']:
        Path(directory).mkdir(exist_ok=True)
    print("✅ Created required directories")
    
    # Create .env template if it doesn't exist
    env_path = Path('.env')
    if not env_path.exists():
        with open(env_path, 'w') as f:
            f.write("# GST Intelligence Platform Environment Variables\n")
            f.write("RAPIDAPI_KEY=your_rapidapi_key_here\n")
            f.write("ANTHROPIC_API_KEY=your_anthropic_api_key_here\n")
            f.write("RAPIDAPI_HOST=gst-return-status.p.rapidapi.com\n")
        print("✅ Created .env template file")
    
    # Run database initialization
    try:
        import quick_db_fix
        quick_db_fix.quick_database_setup()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Could not initialize database: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--fix":
        fix_common_issues()
    
    run_diagnostics()
    
    print("\n💡 Tips:")
    print("- Run 'python fix_issues.py --fix' to attempt automatic fixes")
    print("- Check the README.md for detailed setup instructions")
    print("- Visit http://localhost:8000 after starting the app")
    print("- Use http://localhost:8001 to view the database")