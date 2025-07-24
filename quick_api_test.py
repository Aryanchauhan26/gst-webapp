#!/usr/bin/env python3
"""
QUICK API TEST SCRIPT
Run this script to quickly test your GST and Anthropic API keys
Usage: python quick_api_test.py
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*50}")
    print(f"🔧 {msg}")
    print(f"{'='*50}{Colors.END}")

async def test_gst_api(api_key, host):
    """Test GST API with a sample GSTIN"""
    print_header("TESTING GST API")
    
    if not api_key:
        print_error("RAPIDAPI_KEY not found in environment variables")
        return False
    
    print_info(f"API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else api_key}")
    print_info(f"Host: {host}")
    
    test_gstin = "29AAAPL2356Q1ZS"  # Sample GSTIN for testing
    
    try:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host,
            "Content-Type": "application/json"
        }
        
        url = f"https://{host}/gstin/{test_gstin}"
        print_info(f"Testing URL: {url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            
        print_info(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print_success("GST API is working correctly!")
            data = response.json()
            print_info(f"Sample response keys: {list(data.keys())[:5]}")
            return True
        elif response.status_code == 401:
            print_error("Invalid API key (401 Unauthorized)")
            print_warning("Check your RAPIDAPI_KEY in RapidAPI dashboard")
            return False
        elif response.status_code == 403:
            print_error("API key lacks permission (403 Forbidden)")
            print_warning("Subscribe to the GST API service in RapidAPI")
            return False
        elif response.status_code == 404:
            print_success("GST API is working (404 for test GSTIN is normal)")
            return True
        elif response.status_code == 429:
            print_error("Rate limit exceeded (429)")
            print_warning("Wait a moment and try again")
            return False
        else:
            print_error(f"Unexpected response: {response.status_code}")
            print_info(f"Response text: {response.text[:200]}")
            return False
            
    except httpx.TimeoutException:
        print_error("Request timeout - API server might be slow")
        return False
    except httpx.ConnectError:
        print_error("Connection error - check your internet connection")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        return False

async def test_anthropic_api(api_key):
    """Test Anthropic API with a simple request"""
    print_header("TESTING ANTHROPIC API")
    
    if not api_key:
        print_error("ANTHROPIC_API_KEY not found in environment variables")
        return False
    
    print_info(f"API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else api_key}")
    
    # Check API key format
    if not api_key.startswith('sk-ant-'):
        print_error("Invalid API key format - should start with 'sk-ant-'")
        return False
    
    try:
        # Try to import anthropic
        try:
            import anthropic
            print_success("Anthropic package is installed")
        except ImportError:
            print_error("Anthropic package not installed")
            print_warning("Install with: pip install anthropic")
            return False
        
        # Initialize client
        client = anthropic.Anthropic(api_key=api_key)
        print_info("Client initialized successfully")
        
        # Make test request
        print_info("Making test request...")
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=20,
            messages=[{"role": "user", "content": "Say 'API test successful'"}]
        )
        
        if response and response.content:
            response_text = response.content[0].text
            print_success("Anthropic API is working correctly!")
            print_info(f"Test response: {response_text}")
            return True
        else:
            print_error("Empty response from API")
            return False
            
    except anthropic.AuthenticationError:
        print_error("Invalid API key - authentication failed")
        print_warning("Check your ANTHROPIC_API_KEY in Anthropic Console")
        return False
    except anthropic.PermissionDeniedError:
        print_error("Permission denied - API key lacks required permissions")
        return False
    except anthropic.RateLimitError:
        print_error("Rate limit exceeded - wait and try again")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        return False

def check_environment():
    """Check environment setup"""
    print_header("CHECKING ENVIRONMENT")
    
    # Check if .env file exists
    if os.path.exists('.env'):
        print_success(".env file found")
        
        # Try to load it
        load_dotenv(verbose=True)
        print_success("Environment variables loaded from .env")
    else:
        print_warning(".env file not found - will use system environment variables")
    
    # Check API keys
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    rapidapi_host = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")
    
    print_info(f"RAPIDAPI_KEY: {'✅ SET' if rapidapi_key else '❌ NOT SET'}")
    if rapidapi_key:
        print_info(f"  Length: {len(rapidapi_key)} characters")
    
    print_info(f"ANTHROPIC_API_KEY: {'✅ SET' if anthropic_key else '❌ NOT SET'}")
    if anthropic_key:
        print_info(f"  Length: {len(anthropic_key)} characters")
        print_info(f"  Format: {'✅ Valid' if anthropic_key.startswith('sk-ant-') else '❌ Invalid'}")
    
    print_info(f"RAPIDAPI_HOST: {rapidapi_host}")
    
    return rapidapi_key, anthropic_key, rapidapi_host

async def main():
    """Main test function"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("🚀 GST INTELLIGENCE PLATFORM - API KEY TESTER")
    print("=" * 50)
    print(f"{Colors.END}")
    
    # Check environment
    rapidapi_key, anthropic_key, rapidapi_host = check_environment()
    
    # Test APIs
    gst_success = False
    ai_success = False
    
    if rapidapi_key:
        gst_success = await test_gst_api(rapidapi_key, rapidapi_host)
    else:
        print_error("Skipping GST API test - no API key found")
    
    if anthropic_key:
        ai_success = await test_anthropic_api(anthropic_key)
    else:
        print_error("Skipping Anthropic API test - no API key found")
    
    # Final summary
    print_header("FINAL RESULTS")
    
    if gst_success:
        print_success("GST API: Working correctly")
    else:
        print_error("GST API: Not working or not configured")
    
    if ai_success:
        print_success("Anthropic API: Working correctly")
    else:
        print_error("Anthropic API: Not working or not configured")
    
    if gst_success and ai_success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL APIS ARE WORKING! Your app should work correctly.{Colors.END}")
    elif gst_success or ai_success:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  PARTIAL SUCCESS: Some APIs are working. Check the errors above.{Colors.END}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ NO APIS WORKING: Please fix the API key issues above.{Colors.END}")
        print(f"{Colors.YELLOW}💡 Quick fixes:")
        print(f"   1. Check your .env file has the correct keys")
        print(f"   2. Verify API keys in RapidAPI and Anthropic dashboards")
        print(f"   3. Make sure you have active subscriptions{Colors.END}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Test failed with error: {e}{Colors.END}")