# remove_duplicate_tooltips.py
import os
import re

def clean_tooltip_css(file_path):
    """Remove all CSS-based tooltip rules"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove all tooltip CSS rules
        patterns = [
            r'\.tooltip::after\s*\{[^}]+\}',
            r'\.tooltip:hover::after\s*\{[^}]+\}',
            r'\.tooltip::before\s*\{[^}]+\}',
            r'\.tooltip:hover::before\s*\{[^}]+\}',
        ]
        
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # Clean up extra whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Cleaned tooltip CSS from {file_path}")
        
    except Exception as e:
        print(f"❌ Error cleaning {file_path}: {e}")

def main():
    templates = [
        'templates/results.html',
        'templates/history.html',
        'templates/analytics.html',
        'templates/index.html'
    ]
    
    print("🧹 Removing all duplicate CSS tooltip systems...")
    
    for template in templates:
        if os.path.exists(template):
            clean_tooltip_css(template)
    
    print("\n✅ All duplicate tooltip CSS removed!")
    print("Now only the enhanced JavaScript tooltip system will work.")

if __name__ == "__main__":
    main()