#!/usr/bin/env python3
"""
API Test Script - Direct API Testing
Run this to test your RapidAPI and Anthropic API configuration
"""

import os
import asyncio
import httpx
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_rapidapi():
    """Test RapidAPI GST service directly"""
    print("🧪 Testing RapidAPI GST Service...")
    print("=" * 50)
    
    # Get environment variables
    api_key = os.getenv("RAPIDAPI_KEY", "").strip()
    host = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com").strip()
    
    print(f"🔑 API Key: {'✅ SET' if api_key else '❌ MISSING'} (Length: {len(api_key)})")
    print(f"🌐 Host: {host}")
    
    if not api_key:
        print("❌ RAPIDAPI_KEY not found in environment variables")
        return False
    
    # Test GSTIN
    test_gstin = "29AAAPL2356Q1ZS"
    
    # Headers exactly as they should be
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": host,
    }
    
    print(f"📋 Headers: {headers}")
    
    # Try different URL patterns that RapidAPI typically uses
    url_patterns = [
        f"https://{host}/gstin/{test_gstin}",
        f"https://{host}/api/gstin/{test_gstin}",
        f"https://{host}/api/v1/gstin/{test_gstin}",
        f"https://{host}/gst/{test_gstin}",
        f"https://{host}/search/{test_gstin}",
        f"https://{host}/{test_gstin}",
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, url in enumerate(url_patterns):
            try:
                print(f"\n🔄 Attempt {i+1}: {url}")
                
                response = await client.get(url, headers=headers)
                
                print(f"📊 Status Code: {response.status_code}")
                print(f"📊 Response Headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"✅ SUCCESS! Got data for {test_gstin}")
                        print(f"📝 Company Name: {data.get('lgnm', 'N/A')}")
                        print(f"📝 Status: {data.get('sts', 'N/A')}")
                        print(f"📝 Data Keys: {list(data.keys())}")
                        return True
                    except json.JSONDecodeError:
                        print(f"⚠️ Got 200 but invalid JSON: {response.text[:200]}")
                
                elif response.status_code == 401:
                    print("❌ 401 Unauthorized - Your API key might be invalid")
                    print(f"Response: {response.text[:200]}")
                
                elif response.status_code == 403:
                    print("❌ 403 Forbidden - API key might not have access to this endpoint")
                    print(f"Response: {response.text[:200]}")
                
                elif response.status_code == 404:
                    print("⚠️ 404 Not Found - This endpoint doesn't exist")
                
                elif response.status_code == 429:
                    print("⚠️ 429 Rate Limited")
                
                else:
                    print(f"⚠️ HTTP {response.status_code}: {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
    
    print("❌ All RapidAPI endpoints failed")
    return False

async def test_anthropic_api():
    """Test Anthropic API directly"""
    print("\n🤖 Testing Anthropic API...")
    print("=" * 50)
    
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    
    print(f"🔑 API Key: {'✅ SET' if api_key else '❌ MISSING'} (Length: {len(api_key)})")
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment variables")
        return False
    
    # Check API key format
    if not api_key.startswith('sk-ant-'):
        print(f"❌ Invalid API key format. Expected 'sk-ant-', got: {api_key[:15]}...")
        return False
    
    try:
        import anthropic
        print("✅ Anthropic package imported successfully")
    except ImportError:
        print("❌ Anthropic package not installed. Run: pip install anthropic")
        return False
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        print("✅ Anthropic client initialized")
        
        # Test with a simple message
        test_prompt = """
        Analyze this GST company briefly:
        
        Company: Test Company Pvt Ltd
        Status: Active
        Returns Filed: 8
        GSTIN: 29AAAPL2356Q1ZS
        
        Provide a 2-sentence professional analysis.
        """
        
        print("🔄 Sending test request...")
        
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            temperature=0.3,
            messages=[{"role": "user", "content": test_prompt}]
        )
        
        if response and response.content:
            synopsis = response.content[0].text
            print("✅ SUCCESS! Anthropic API working")
            print(f"📝 Response: {synopsis[:100]}...")
            return True
        else:
            print("❌ Got empty response from Anthropic API")
            return False
            
    except Exception as e:
        print(f"❌ Anthropic API Error: {e}")
        return False

async def main():
    """Run all API tests"""
    print("🚀 API Configuration Test Suite")
    print("=" * 50)
    
    # Test environment variables
    print("📋 Environment Variables:")
    print(f"RAPIDAPI_KEY: {'✅' if os.getenv('RAPIDAPI_KEY') else '❌'}")
    print(f"RAPIDAPI_HOST: {'✅' if os.getenv('RAPIDAPI_HOST') else '❌'}")
    print(f"ANTHROPIC_API_KEY: {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'}")
    print()
    
    # Test APIs
    rapidapi_works = await test_rapidapi()
    anthropic_works = await test_anthropic_api()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 TEST RESULTS SUMMARY")
    print("=" * 50)
    print(f"RapidAPI GST: {'✅ WORKING' if rapidapi_works else '❌ FAILED'}")
    print(f"Anthropic AI: {'✅ WORKING' if anthropic_works else '❌ FAILED'}")
    
    if rapidapi_works and anthropic_works:
        print("\n🎉 ALL APIS WORKING! Your backend should work now.")
    else:
        print("\n🚨 ISSUES DETECTED:")
        if not rapidapi_works:
            print("- Fix your RapidAPI configuration")
            print("- Check your API key and endpoint URL")
            print("- Verify the API is active in RapidAPI dashboard")
        if not anthropic_works:
            print("- Fix your Anthropic API configuration")
            print("- Check your API key format (should start with 'sk-ant-')")
            print("- Verify the API key is active")
    
    print("\n📝 Next Steps:")
    print("1. Fix any issues identified above")
    print("2. Update your .env file with correct values")
    print("3. Restart your application")
    print("4. Test the /debug/api-status endpoint")

if __name__ == "__main__":
    asyncio.run(main())