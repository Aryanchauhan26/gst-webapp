#!/usr/bin/env python3
"""
Quick installation script for web search functionality
"""

import subprocess
import sys

def install_search_deps():
    """Install the web search dependency"""
    print("🔧 Installing web search capability...")
    
    try:
        # Install googlesearch-python
        subprocess.check_call([sys.executable, "-m", "pip", "install", "googlesearch-python"])
        print("✅ Web search capability installed successfully!")
        
        print("\n📝 Testing import...")
        from googlesearch import search
        print("✅ Import successful! Web search is ready.")
        
        print("\n💡 Your AI synopsis will now search the web for company information!")
        
    except subprocess.CalledProcessError:
        print("❌ Failed to install. Try manually: pip install googlesearch-python")
    except ImportError:
        print("⚠️  Package installed but import failed. Restart your Python environment.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    install_search_deps()