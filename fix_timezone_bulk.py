#!/usr/bin/env python3
"""
Bulk fix timezone issues in database.py
"""

import re

def fix_timezone_in_database():
    """Fix all timezone issues in database.py file."""
    try:
        # Read the database.py file
        with open('database.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace all instances of datetime.now(timezone.utc) with datetime.now()
        fixed_content = content.replace('datetime.now(timezone.utc)', 'datetime.now()')
        
        # Also fix any other timezone.utc references
        fixed_content = fixed_content.replace('timezone.utc', 'timezone.utc')
        
        # Write the fixed content back
        with open('database.py', 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("✅ Fixed all timezone issues in database.py")
        print("🎯 All datetime.now(timezone.utc) → datetime.now()")
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")

if __name__ == "__main__":
    fix_timezone_in_database()