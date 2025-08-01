#!/usr/bin/env python3
"""
Startup Script for GST Intelligence Platform
This script handles proper startup with API validation
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def validate_environment():
    """Validate all required environment variables"""
    logger.info("🔍 Validating environment configuration...")
    
    required_vars = {
        'RAPIDAPI_KEY': 'RapidAPI key for GST data',
        'ANTHROPIC_API_KEY': 'Anthropic API key for AI features',
        'POSTGRES_DSN': 'PostgreSQL database connection string'
    }
    
    missing_vars = []
    invalid_vars = []
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name, '').strip()
        
        if not value:
            missing_vars.append(f"❌ {var_name}: {description}")
        else:
            logger.info(f"✅ {var_name}: Configured (length: {len(value)})")
            
            # Validate specific formats
            if var_name == 'ANTHROPIC_API_KEY' and not value.startswith('sk-ant-'):
                invalid_vars.append(f"❌ {var_name}: Invalid format (should start with 'sk-ant-')")
            elif var_name == 'RAPIDAPI_KEY' and len(value) < 20:
                invalid_vars.append(f"❌ {var_name}: Seems too short (length: {len(value)})")
    
    if missing_vars or invalid_vars:
        logger.error("🚨 Environment configuration issues detected:")
        for var in missing_vars + invalid_vars:
            logger.error(var)
        return False
    
    logger.info("✅ All environment variables validated successfully")
    return True

async def test_api_connections():
    """Test API connections before starting the server"""
    logger.info("🧪 Testing API connections...")
    
    try:
        # Import your API clients
        from main import api_client, ai_client
        
        # Test GST API
        if api_client:
            try:
                test_result = await api_client.fetch_gstin_data("29AAAPL2356Q1ZS")
                if test_result and test_result.get("lgnm"):
                    logger.info("✅ GST API connection successful")
                else:
                    logger.warning("⚠️ GST API returned empty data - may use fallback")
            except Exception as e:
                logger.warning(f"⚠️ GST API test failed: {e}")
        else:
            logger.error("❌ GST API client not initialized")
        
        # Test Anthropic API
        if ai_client and ai_client.is_available:
            try:
                test_data = {"lgnm": "Test Company", "sts": "Active"}
                from main import get_enhanced_ai_synopsis
                synopsis = await get_enhanced_ai_synopsis(test_data)
                if synopsis and len(synopsis) > 10:
                    logger.info("✅ Anthropic API connection successful")
                else:
                    logger.warning("⚠️ Anthropic API returned empty response")
            except Exception as e:
                logger.warning(f"⚠️ Anthropic API test failed: {e}")
        else:
            logger.warning("⚠️ Anthropic API client not available")
        
    except Exception as e:
        logger.error(f"❌ API connection testing failed: {e}")
        return False
    
    return True

async def initialize_database():
    """Initialize database connection"""
    logger.info("📊 Initializing database...")
    
    try:
        from main import db
        await db.initialize()
        
        # Test database connection
        async with db.pool.acquire() as conn:
            await conn.execute("SELECT 1")
        
        logger.info("✅ Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

async def startup_checks():
    """Run all startup checks"""
    logger.info("🚀 Starting GST Intelligence Platform...")
    logger.info("=" * 60)
    
    # Step 1: Validate environment
    if not await validate_environment():
        logger.error("❌ Environment validation failed. Please fix your .env file.")
        return False
    
    # Step 2: Initialize database
    if not await initialize_database():
        logger.error("❌ Database initialization failed. Please check your database connection.")
        return False
    
    # Step 3: Test API connections
    await test_api_connections()  # This is non-critical, just warnings
    
    logger.info("=" * 60)
    logger.info("✅ All startup checks completed successfully!")
    logger.info("🌐 Server will start shortly...")
    
    return True

def start_server():
    """Start the FastAPI server"""
    import uvicorn
    
    # Get port from environment (for Render/Heroku compatibility)
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"🌐 Starting server on {host}:{port}")
    
    # Start the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Disable reload in production
        log_level="info",
        access_log=True
    )

async def main():
    """Main startup function"""
    try:
        # Run startup checks
        startup_success = await startup_checks()
        
        if not startup_success:
            logger.error("❌ Startup checks failed. Exiting...")
            sys.exit(1)
        
        # If we get here, everything is good
        logger.info("🎉 Ready to start server!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed with critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run startup checks
    asyncio.run(main())
    
    # Start the server
    start_server()