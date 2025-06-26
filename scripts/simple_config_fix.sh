#!/bin/bash

# =============================================================================
# Simple Config.py Fix - Add Module-Level Attributes
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_status $BLUE "🔧 Adding module-level attributes to config.py..."

# Create backup
cp config.py config.py.backup.$(date +%Y%m%d_%H%M%S)
print_status $GREEN "✅ Backup created"

# Add module-level attributes at the end of config.py
cat >> config.py << 'EOF'

=============================================================================
 MODULE-LEVEL ATTRIBUTES FOR BACKWARD COMPATIBILITY
=============================================================================

POSTGRES_DSN = settings.POSTGRES_DSN
RAPIDAPI_KEY = settings.RAPIDAPI_KEY
RAPIDAPI_HOST = settings.RAPIDAPI_HOST
ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY
SECRET_KEY = settings.SECRET_KEY
ADMIN_USERS = settings.ADMIN_USERS
SESSION_DURATION = settings.SESSION_DURATION
RATE_LIMIT_REQUESTS = settings.RATE_LIMIT_REQUESTS
RATE_LIMIT_WINDOW = settings.RATE_LIMIT_WINDOW
RAZORPAY_KEY_ID = settings.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = settings.RAZORPAY_KEY_SECRET
RAZORPAY_ENVIRONMENT = settings.RAZORPAY_ENVIRONMENT
REDIS_URL = settings.REDIS_URL
DEBUG = settings.DEBUG
ENVIRONMENT = settings.ENVIRONMENT
is_production = settings.is_production

# Export all important attributes
__all__ = [
    'settings', 'POSTGRES_DSN', 'RAPIDAPI_KEY', 'RAPIDAPI_HOST', 'ANTHROPIC_API_KEY',
    'SECRET_KEY', 'ADMIN_USERS', 'SESSION_DURATION', 'RATE_LIMIT_REQUESTS', 
    'RATE_LIMIT_WINDOW', 'RAZORPAY_KEY_ID', 'RAZORPAY_KEY_SECRET', 'RAZORPAY_ENVIRONMENT',
    'REDIS_URL', 'DEBUG', 'ENVIRONMENT', 'is_production'
]
EOF

print_status $GREEN "✅ Module-level attributes added"

# Test the fix
print_status $YELLOW "🧪 Testing configuration access..."
python3 -c "
import config

# Test the specific attributes that main.py needs
try:
    rate_requests = config.RATE_LIMIT_REQUESTS
    rate_window = config.RATE_LIMIT_WINDOW
    secret_key = config.SECRET_KEY
    admin_users = config.ADMIN_USERS
    session_duration = config.SESSION_DURATION
    
    print(f'✅ RATE_LIMIT_REQUESTS = {rate_requests}')
    print(f'✅ RATE_LIMIT_WINDOW = {rate_window}')
    print(f'✅ SECRET_KEY = {secret_key[:10]}...')
    print(f'✅ ADMIN_USERS = {admin_users}')
    print(f'✅ SESSION_DURATION = {session_duration}')
    print('🎉 All module-level attributes accessible!')
    
except AttributeError as e:
    print(f'❌ AttributeError: {e}')
    exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    print_status $GREEN "✅ Configuration test passed!"
else
    print_status $RED "❌ Configuration test failed"
    exit 1
fi

# Test main.py import specifically
print_status $YELLOW "🧪 Testing main.py compatibility..."
python3 -c "
import config

# Test the exact line that was failing in main.py
try:
    # Simulate the RateLimiter.__init__ line
    max_requests = config.RATE_LIMIT_REQUESTS
    window_seconds = config.RATE_LIMIT_WINDOW
    
    print(f'✅ RateLimiter can access config.RATE_LIMIT_REQUESTS = {max_requests}')
    print(f'✅ RateLimiter can access config.RATE_LIMIT_WINDOW = {window_seconds}')
    print('🎉 main.py should now start without AttributeError!')
    
except Exception as e:
    print(f'❌ Error: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    print_status $GREEN "🎉 SUCCESS! Config.py is now compatible with main.py"
    print_status $BLUE "📋 What was fixed:"
    echo "  ✅ Added module-level RATE_LIMIT_REQUESTS attribute"
    echo "  ✅ Added module-level RATE_LIMIT_WINDOW attribute" 
    echo "  ✅ Added all other required module-level attributes"
    echo "  ✅ Maintained backward compatibility"
    echo ""
    print_status $GREEN "🚀 Your application should now start successfully!"
    echo "Run: python3 main.py"
else
    print_status $RED "❌ Test failed"
    exit 1
fi