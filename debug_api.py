#!/usr/bin/env python3
"""
Debug script to test GST API response
Run this to verify your API key and response structure
"""

import os
import asyncio
import httpx
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_api():
    """Test the GST API with a sample GSTIN"""
    
    api_key = os.getenv("RAPIDAPI_KEY")
    api_host = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")
    
    if not api_key:
        print("❌ RAPIDAPI_KEY not found in environment variables")
        print("Please make sure you have a .env file with RAPIDAPI_KEY=your_key_here")
        return
    
    print(f"✅ API Key found: {api_key[:10]}...")
    print(f"✅ API Host: {api_host}")
    
    # Test GSTIN from your paste.txt
    test_gstin = "27AAJCM9929L1ZM"
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": api_host,
        "User-Agent": "GST-Compliance-Platform/2.0"
    }
    
    url = f"https://{api_host}/free/gstin/{test_gstin}"
    
    print(f"\n🔍 Testing API with GSTIN: {test_gstin}")
    print(f"📡 URL: {url}")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            print("\n⏳ Making API request...")
            resp = await client.get(url, headers=headers)
            
            print(f"\n📊 Response Status: {resp.status_code}")
            print(f"📝 Response Headers: {dict(resp.headers)}")
            
            if resp.status_code == 200:
                json_data = resp.json()
                print("\n✅ API Response received successfully!")
                
                # Pretty print the response
                print("\n📋 Full Response:")
                print(json.dumps(json_data, indent=2))
                
                # Check response structure
                print("\n🔍 Response Structure Analysis:")
                print(f"- Has 'success' field: {'success' in json_data}")
                print(f"- Has 'data' field: {'data' in json_data}")
                
                if 'data' in json_data:
                    data = json_data['data']
                    print(f"\n📊 Data Fields Found:")
                    for key in data.keys():
                        value = data[key]
                        if isinstance(value, (str, int, float, bool)):
                            print(f"  - {key}: {value}")
                        elif isinstance(value, list):
                            print(f"  - {key}: List with {len(value)} items")
                        elif isinstance(value, dict):
                            print(f"  - {key}: Dictionary with {len(value)} keys")
                        else:
                            print(f"  - {key}: {type(value).__name__}")
                
                # Test data extraction
                if json_data.get("success") and "data" in json_data:
                    company_data = json_data["data"]
                elif "data" in json_data:
                    company_data = json_data["data"]
                else:
                    company_data = json_data
                
                print(f"\n✅ Company Name: {company_data.get('lgnm', 'Not found')}")
                print(f"✅ GSTIN: {company_data.get('gstin', 'Not found')}")
                print(f"✅ Status: {company_data.get('sts', 'Not found')}")
                
            else:
                print(f"\n❌ API Error: {resp.status_code}")
                print(f"Response: {resp.text}")
                
    except httpx.TimeoutException:
        print("\n❌ Request timed out. The API might be slow or unavailable.")
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def test_multiple_gstins():
    """Test with multiple GSTINs to see response consistency"""
    test_gstins = [
        "27AAJCM9929L1ZM",  # From your paste.txt
        "29AABCT1332L1ZN",  # Karnataka GSTIN
        "07AAGCC2701A1Z5",  # Delhi GSTIN
    ]
    
    print("\n🔍 Testing multiple GSTINs...")
    for gstin in test_gstins:
        print(f"\n--- Testing {gstin} ---")
        await test_api_simple(gstin)
        await asyncio.sleep(1)  # Rate limiting

async def test_api_simple(gstin):
    """Simple API test for a specific GSTIN"""
    api_key = os.getenv("RAPIDAPI_KEY")
    api_host = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")
    
    if not api_key:
        return
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": api_host,
    }
    
    url = f"https://{api_host}/free/gstin/{gstin}"
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data:
                    company = data['data']
                    print(f"✅ {company.get('lgnm', 'Unknown')} - Status: {company.get('sts', 'Unknown')}")
                else:
                    print(f"⚠️  Different response structure")
            else:
                print(f"❌ Error: {resp.status_code}")
    except Exception as e:
        print(f"❌ {type(e).__name__}")

if __name__ == "__main__":
    print("🔧 GST API Debug Tool")
    print("=" * 50)
    
    # Run the test
    asyncio.run(test_api())
    
    print("\n" + "=" * 50)
    print("\n💡 Next Steps:")
    print("1. If the API test was successful, your app should work now")
    print("2. If you see authentication errors, check your API key")
    print("3. If the response structure is different, we may need to adjust the code")
    print("4. Run 'python main.py' to start your application")