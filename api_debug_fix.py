#!/usr/bin/env python3
"""
FIXED: API Configuration and Debug Tools for GST Intelligence Platform
This addresses the issues with GST API and Anthropic API keys not working
"""

import os
import logging
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ISSUE 1: Load environment variables FIRST and with debugging
def load_environment_with_debug():
    """Load environment variables with detailed debugging"""
    print("🔍 DEBUG: Loading environment variables...")
    
    # Try to load from .env file
    env_loaded = load_dotenv(verbose=True)
    print(f"📁 .env file loaded: {env_loaded}")
    
    # Check if .env file exists
    if os.path.exists('.env'):
        print("✅ .env file exists")
        with open('.env', 'r') as f:
            content = f.read()
            print(f"📄 .env file content length: {len(content)} characters")
            # Don't print actual content for security
    else:
        print("❌ .env file not found")
    
    # Check environment variables
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    rapidapi_host = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")
    
    print(f"🔑 RAPIDAPI_KEY: {'✅ SET' if rapidapi_key else '❌ NOT SET'}")
    if rapidapi_key:
        print(f"    Length: {len(rapidapi_key)} characters")
        print(f"    Starts with: {rapidapi_key[:10]}...")
        print(f"    Contains spaces: {'Yes' if ' ' in rapidapi_key else 'No'}")
    
    print(f"🤖 ANTHROPIC_API_KEY: {'✅ SET' if anthropic_key else '❌ NOT SET'}")
    if anthropic_key:
        print(f"    Length: {len(anthropic_key)} characters")
        print(f"    Starts with: {anthropic_key[:10]}...")
        print(f"    Format check: {'✅ Valid' if anthropic_key.startswith('sk-ant-') else '❌ Invalid format'}")
        print(f"    Contains spaces: {'Yes' if ' ' in anthropic_key else 'No'}")
    
    print(f"🌐 RAPIDAPI_HOST: {rapidapi_host}")
    
    return rapidapi_key, anthropic_key, rapidapi_host

# Load environment with debugging
RAPIDAPI_KEY, ANTHROPIC_API_KEY, RAPIDAPI_HOST = load_environment_with_debug()

# ISSUE 2: Enhanced GST API Client with better error handling and debugging
class EnhancedGSTAPIClient:
    """Enhanced GST API Client with comprehensive debugging"""
    
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key.strip() if api_key else None  # Remove whitespace
        self.host = host.strip() if host else None
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
            "Content-Type": "application/json"
        }
        
        # Debug initialization
        print(f"🔧 Initializing GST API Client:")
        print(f"    API Key: {'✅ Valid' if self.api_key else '❌ Missing'}")
        print(f"    Host: {self.host}")
        print(f"    Headers prepared: {bool(self.headers)}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test API connection and credentials"""
        print("🧪 Testing GST API connection...")
        
        if not self.api_key:
            return {"success": False, "error": "API key is missing"}
        
        try:
            # Test with a known valid GSTIN for connection testing
            test_gstin = "29AAAPL2356Q1ZS"  # Sample GSTIN
            
            async with httpx.AsyncClient() as client:
                print(f"📡 Making test request to: https://{self.host}/gstin/{test_gstin}")
                print(f"🔑 Using headers: {dict(self.headers)}")
                
                response = await client.get(
                    f"https://{self.host}/gstin/{test_gstin}",
                    headers=self.headers,
                    timeout=30.0
                )
                
                print(f"📊 Response status: {response.status_code}")
                print(f"📊 Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True, 
                        "message": "API connection successful",
                        "test_data": data
                    }
                elif response.status_code == 401:
                    return {
                        "success": False, 
                        "error": "Invalid API key - 401 Unauthorized",
                        "status_code": response.status_code,
                        "response_text": response.text[:500]
                    }
                elif response.status_code == 403:
                    return {
                        "success": False, 
                        "error": "API key doesn't have permission - 403 Forbidden",
                        "status_code": response.status_code,
                        "response_text": response.text[:500]
                    }
                elif response.status_code == 404:
                    return {
                        "success": True,  # 404 is OK for test GSTIN, means API is working
                        "message": "API is working (404 for test GSTIN is normal)",
                        "status_code": response.status_code
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Unexpected response: {response.status_code}",
                        "status_code": response.status_code,
                        "response_text": response.text[:500]
                    }
                    
        except httpx.TimeoutException:
            return {"success": False, "error": "API request timeout"}
        except httpx.ConnectError:
            return {"success": False, "error": "Cannot connect to API server"}
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}
    
    async def fetch_gstin_data(self, gstin: str) -> Dict:
        """Fetch GSTIN data with enhanced error handling"""
        print(f"🔍 Fetching data for GSTIN: {gstin}")
        
        if not self.api_key:
            raise Exception("GST API key is not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"https://{self.host}/gstin/{gstin}"
                print(f"📡 Request URL: {url}")
                
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0
                )
                
                print(f"📊 Response: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Data received for {gstin}")
                    return data
                elif response.status_code == 401:
                    raise Exception("Invalid API key - please check your RAPIDAPI_KEY")
                elif response.status_code == 403:
                    raise Exception("API key doesn't have permission for this endpoint")
                elif response.status_code == 404:
                    raise Exception(f"Company not found for GSTIN: {gstin}")
                elif response.status_code == 429:
                    raise Exception("API rate limit exceeded")
                else:
                    error_text = response.text[:200]
                    raise Exception(f"API error {response.status_code}: {error_text}")
                    
        except httpx.TimeoutException:
            raise Exception("API request timeout - please try again")
        except httpx.ConnectError:
            raise Exception("Cannot connect to GST API server")
        except Exception as e:
            logger.error(f"GST API error: {e}")
            raise

# ISSUE 3: Enhanced Anthropic AI Client with better debugging
class EnhancedAnthropicClient:
    """Enhanced Anthropic client with debugging capabilities"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or os.getenv("ANTHROPIC_API_KEY", "")).strip()
        self.is_available = False
        
        print(f"🤖 Initializing Anthropic AI Client:")
        print(f"    API Key: {'✅ Valid' if self.api_key else '❌ Missing'}")
        
        if not self.api_key:
            print("❌ ANTHROPIC_API_KEY not found")
            return
        
        # Validate API key format
        if not self.api_key.startswith('sk-ant-'):
            print(f"❌ Invalid API key format. Expected 'sk-ant-...', got '{self.api_key[:10]}...'")
            return
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.is_available = True
            print("✅ Anthropic client initialized successfully")
        except ImportError:
            print("❌ Anthropic package not installed")
        except Exception as e:
            print(f"❌ Failed to initialize Anthropic client: {e}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Anthropic API connection"""
        print("🧪 Testing Anthropic API connection...")
        
        if not self.is_available:
            return {"success": False, "error": "Anthropic client not available"}
        
        try:
            # Make a simple test request
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            return {
                "success": True, 
                "message": "Anthropic API connection successful",
                "response": response.content[0].text if response.content else "No content"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Anthropic API error: {str(e)}"}
    
    async def get_synopsis(self, company_data: Dict) -> Optional[str]:
        """Generate synopsis with error handling"""
        if not self.is_available:
            print("⚠️ Anthropic client not available, using fallback")
            return None
        
        try:
            # Your existing synopsis generation logic here
            company_name = company_data.get('lgnm', 'Unknown Company')
            
            prompt = f"""
            Analyze this GST company data and provide a brief professional synopsis:
            Company: {company_name}
            Status: {company_data.get('sts', 'Unknown')}
            Registration: {company_data.get('rgdt', 'Unknown')}
            
            Provide a 2-3 sentence professional analysis.
            """
            
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text if response.content else None
            
        except Exception as e:
            print(f"❌ Synopsis generation failed: {e}")
            return None

# ISSUE 4: Initialize clients with proper error handling
def initialize_api_clients():
    """Initialize API clients with comprehensive error checking"""
    print("\n🚀 Initializing API clients...")
    
    # GST API Client
    gst_client = None
    if RAPIDAPI_KEY and RAPIDAPI_HOST:
        try:
            gst_client = EnhancedGSTAPIClient(RAPIDAPI_KEY, RAPIDAPI_HOST)
            print("✅ GST API client created")
        except Exception as e:
            print(f"❌ Failed to create GST API client: {e}")
    else:
        print("❌ GST API client not created - missing credentials")
    
    # Anthropic AI Client
    ai_client = None
    if ANTHROPIC_API_KEY:
        try:
            ai_client = EnhancedAnthropicClient(ANTHROPIC_API_KEY)
            print("✅ Anthropic AI client created")
        except Exception as e:
            print(f"❌ Failed to create Anthropic AI client: {e}")
    else:
        print("❌ Anthropic AI client not created - missing API key")
    
    return gst_client, ai_client

# Initialize clients
enhanced_gst_client, enhanced_ai_client = initialize_api_clients()

# ISSUE 5: Add debug endpoints to test the APIs
async def debug_api_status():
    """Debug function to test both APIs"""
    print("\n🔧 DEBUGGING API STATUS:")
    print("=" * 50)
    
    results = {
        "environment": {
            "rapidapi_key_set": bool(RAPIDAPI_KEY),
            "anthropic_key_set": bool(ANTHROPIC_API_KEY),
            "rapidapi_host": RAPIDAPI_HOST
        },
        "gst_api": None,
        "anthropic_api": None
    }
    
    # Test GST API
    if enhanced_gst_client:
        print("🧪 Testing GST API...")
        gst_result = await enhanced_gst_client.test_connection()
        results["gst_api"] = gst_result
        print(f"GST API Status: {'✅ SUCCESS' if gst_result['success'] else '❌ FAILED'}")
        if not gst_result['success']:
            print(f"Error: {gst_result['error']}")
    else:
        results["gst_api"] = {"success": False, "error": "Client not initialized"}
        print("❌ GST API client not available")
    
    # Test Anthropic API
    if enhanced_ai_client:
        print("🧪 Testing Anthropic API...")
        ai_result = await enhanced_ai_client.test_connection()
        results["anthropic_api"] = ai_result
        print(f"Anthropic API Status: {'✅ SUCCESS' if ai_result['success'] else '❌ FAILED'}")
        if not ai_result['success']:
            print(f"Error: {ai_result['error']}")
    else:
        results["anthropic_api"] = {"success": False, "error": "Client not initialized"}
        print("❌ Anthropic AI client not available")
    
    print("=" * 50)
    return results

# Export the enhanced clients for use in main.py
__all__ = [
    'enhanced_gst_client', 
    'enhanced_ai_client', 
    'debug_api_status',
    'RAPIDAPI_KEY',
    'ANTHROPIC_API_KEY',
    'RAPIDAPI_HOST'
]

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Run debug test
        results = await debug_api_status()
        print("\n📊 Final Results:")
        print(f"Environment Variables: {results['environment']}")
        print(f"GST API: {results['gst_api']['success'] if results['gst_api'] else False}")
        print(f"Anthropic API: {results['anthropic_api']['success'] if results['anthropic_api'] else False}")
    
    asyncio.run(main())