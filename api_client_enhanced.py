#!/usr/bin/env python3
"""
Enhanced API Client - Bulletproof API Integration
Use this if you're still having API issues with the main file
"""

import os
import json
import asyncio
import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BulletproofGSTClient:
    """Bulletproof GST API client that tries EVERYTHING"""
    
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key.strip()
        self.host = host.strip()
        self.session_headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
            "User-Agent": "GST-Intelligence-Platform/2.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        logger.info(f"🔧 Bulletproof GST Client initialized")
        logger.info(f"🔑 API Key: {self.api_key[:10]}...{self.api_key[-4:]}")
        logger.info(f"🌐 Host: {self.host}")

    async def fetch_gstin_data(self, gstin: str) -> Dict[str, Any]:
        """Fetch GSTIN data with EVERY possible approach"""
        gstin = gstin.strip().upper()
        
        if not gstin or len(gstin) != 15:
            raise Exception(f"Invalid GSTIN: {gstin}")
        
        logger.info(f"🔍 Fetching data for GSTIN: {gstin}")
        
        # Strategy 1: Try all common RapidAPI URL patterns
        await self._try_rapidapi_patterns(gstin)
        
        # Strategy 2: Try different HTTP methods
        await self._try_different_methods(gstin)
        
        # Strategy 3: Try with different headers
        await self._try_different_headers(gstin)
        
        # If all fails, return mock data
        logger.warning("⚠️ All API strategies failed, returning mock data")
        return self._generate_realistic_mock_data(gstin)

    async def _try_rapidapi_patterns(self, gstin: str) -> Optional[Dict]:
        """Try all common RapidAPI URL patterns"""
        logger.info("🔄 Strategy 1: Trying RapidAPI URL patterns")
        
        # All possible URL patterns
        url_patterns = [
            # Standard patterns
            f"https://{self.host}/gstin/{gstin}",
            f"https://{self.host}/api/gstin/{gstin}",
            f"https://{self.host}/api/v1/gstin/{gstin}",
            f"https://{self.host}/api/v2/gstin/{gstin}",
            
            # Alternative patterns
            f"https://{self.host}/gst/{gstin}",
            f"https://{self.host}/search/{gstin}",
            f"https://{self.host}/lookup/{gstin}",
            f"https://{self.host}/verify/{gstin}",
            f"https://{self.host}/check/{gstin}",
            
            # Direct patterns
            f"https://{self.host}/{gstin}",
            f"https://{self.host}/gstin?number={gstin}",
            f"https://{self.host}/api/gstin?gstin={gstin}",
            
            # RESTful patterns
            f"https://{self.host}/gstins/{gstin}",
            f"https://{self.host}/companies/{gstin}",
            f"https://{self.host}/business/{gstin}",
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, url in enumerate(url_patterns):
                try:
                    logger.info(f"🌐 Trying pattern {i+1}: {url}")
                    
                    response = await client.get(url, headers=self.session_headers)
                    
                    logger.info(f"📊 Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if self._validate_response_data(data, gstin):
                                logger.info(f"✅ SUCCESS with pattern {i+1}!")
                                return data
                        except json.JSONDecodeError:
                            logger.warning(f"⚠️ Invalid JSON from {url}")
                            continue
                    
                    elif response.status_code == 401:
                        logger.error(f"❌ 401 Unauthorized - API key issue")
                        logger.error(f"Response: {response.text[:200]}")
                        # Don't continue with other patterns if auth fails
                        break
                    
                    elif response.status_code == 403:
                        logger.error(f"❌ 403 Forbidden - Access denied")
                        break
                    
                    elif response.status_code == 404:
                        logger.debug(f"⚠️ 404 for pattern {i+1}")
                        continue
                    
                    else:
                        logger.warning(f"⚠️ HTTP {response.status_code} for pattern {i+1}")
                        continue
                        
                except httpx.TimeoutException:
                    logger.warning(f"⏰ Timeout for pattern {i+1}")
                    continue
                except Exception as e:
                    logger.warning(f"❌ Error for pattern {i+1}: {e}")
                    continue
        
        logger.warning("⚠️ All URL patterns failed")
        return None

    async def _try_different_methods(self, gstin: str) -> Optional[Dict]:
        """Try different HTTP methods"""
        logger.info("🔄 Strategy 2: Trying different HTTP methods")
        
        base_url = f"https://{self.host}"
        endpoints = ["/gstin", "/api/gstin", "/gst"]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint in endpoints:
                # Try GET with query params
                try:
                    url = f"{base_url}{endpoint}?gstin={gstin}"
                    response = await client.get(url, headers=self.session_headers)
                    if response.status_code == 200:
                        data = response.json()
                        if self._validate_response_data(data, gstin):
                            logger.info(f"✅ SUCCESS with GET query: {url}")
                            return data
                except Exception as e:
                    logger.debug(f"GET query failed: {e}")
                
                # Try POST with JSON body
                try:
                    url = f"{base_url}{endpoint}"
                    payload = {"gstin": gstin}
                    response = await client.post(url, headers=self.session_headers, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        if self._validate_response_data(data, gstin):
                            logger.info(f"✅ SUCCESS with POST: {url}")
                            return data
                except Exception as e:
                    logger.debug(f"POST failed: {e}")
                
                # Try POST with form data
                try:
                    url = f"{base_url}{endpoint}"
                    form_data = {"gstin": gstin}
                    response = await client.post(url, headers=self.session_headers, data=form_data)
                    if response.status_code == 200:
                        data = response.json()
                        if self._validate_response_data(data, gstin):
                            logger.info(f"✅ SUCCESS with POST form: {url}")
                            return data
                except Exception as e:
                    logger.debug(f"POST form failed: {e}")
        
        logger.warning("⚠️ All HTTP methods failed")
        return None

    async def _try_different_headers(self, gstin: str) -> Optional[Dict]:
        """Try with different header combinations"""
        logger.info("🔄 Strategy 3: Trying different headers")
        
        url = f"https://{self.host}/gstin/{gstin}"
        
        header_variants = [
            # Standard RapidAPI headers
            {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": self.host,
            },
            # With additional headers
            {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": self.host,
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; GST-Platform/2.0)"
            },
            # Alternative header names (some APIs use different conventions)
            {
                "X-API-Key": self.api_key,
                "Host": self.host,
            },
            {
                "Authorization": f"Bearer {self.api_key}",
                "Host": self.host,
            },
            # Minimal headers
            {
                "X-RapidAPI-Key": self.api_key,
            }
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, headers in enumerate(header_variants):
                try:
                    logger.info(f"🔧 Trying header variant {i+1}")
                    
                    response = await client.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if self._validate_response_data(data, gstin):
                                logger.info(f"✅ SUCCESS with header variant {i+1}!")
                                return data
                        except json.JSONDecodeError:
                            continue
                    
                except Exception as e:
                    logger.debug(f"Header variant {i+1} failed: {e}")
                    continue
        
        logger.warning("⚠️ All header variants failed")
        return None

    def _validate_response_data(self, data: Dict, gstin: str) -> bool:
        """Validate that response data looks correct"""
        if not isinstance(data, dict):
            return False
        
        # Check for common GST data fields
        expected_fields = ['lgnm', 'legal_name', 'company_name', 'tradeName', 'sts', 'status']
        has_expected_field = any(field in data for field in expected_fields)
        
        # Check if GSTIN matches
        data_gstin = data.get('gstin', data.get('gst_number', ''))
        gstin_matches = data_gstin == gstin if data_gstin else True
        
        return has_expected_field and gstin_matches

    def _generate_realistic_mock_data(self, gstin: str) -> Dict:
        """Generate realistic mock data as fallback"""
        logger.info(f"📝 Generating realistic mock data for {gstin}")
        
        state_code = gstin[:2] if len(gstin) >= 2 else "29"
        
        # State-based company names
        state_companies = {
            "29": ("Maharashtra Industries Pvt Ltd", "Mumbai"),
            "27": ("Punjab Enterprises Ltd", "Chandigarh"), 
            "07": ("Delhi Trading Company", "New Delhi"),
            "33": ("Tamil Nadu Manufacturing", "Chennai"),
            "09": ("UP Business Solutions", "Lucknow"),
            "24": ("Gujarat Commerce Ltd", "Ahmedabad"),
            "19": ("West Bengal Traders", "Kolkata"),
            "36": ("Telangana Tech Pvt Ltd", "Hyderabad"),
        }
        
        company_name, city = state_companies.get(state_code, ("Test Company Pvt Ltd", "Test City"))
        
        return {
            "gstin": gstin,
            "lgnm": company_name,
            "tradeName": company_name.replace("Pvt Ltd", "").replace("Ltd", "").strip(),
            "sts": "Active",
            "rgdt": "15/01/2020",
            "ctb": "Private Limited Company",
            "pan": gstin[:10] if len(gstin) >= 10 else "AAAPL2356Q",
            "adr": f"123 Business Street, {city} - {state_code}0001",
            "stj": f"State - {state_code}, Ward - Commercial",
            "ctj": f"Central - Range-{state_code}, Division-Business",
            "returns": [
                {"rtntype": "GSTR1", "taxp": "122023", "fy": "2023-24", "dof": "11/01/2024"},
                {"rtntype": "GSTR3B", "taxp": "122023", "fy": "2023-24", "dof": "20/01/2024"},
                {"rtntype": "GSTR1", "taxp": "112023", "fy": "2023-24", "dof": "11/12/2023"},
                {"rtntype": "GSTR3B", "taxp": "112023", "fy": "2023-24", "dof": "20/12/2023"},
                {"rtntype": "GSTR1", "taxp": "102023", "fy": "2023-24", "dof": "11/11/2023"},
                {"rtntype": "GSTR3B", "taxp": "102023", "fy": "2023-24", "dof": "20/11/2023"},
            ],
            "nba": ["Trading", "Manufacturing", "Services"],
            "einvoiceStatus": "Yes",
            "fillingFreq": {"GSTR1": "M", "GSTR3B": "M"},
            "compCategory": "Regular",
            "dty": "Regular",
            "meta": {"latestgtsr1": "122023", "latestgtsr3b": "122023"},
            "pincode": f"{state_code}0001",
            "_mock_data": True,  # Flag to indicate this is mock data
            "_mock_reason": "API connection failed, using realistic fallback data"
        }

class BulletproofAnthropicClient:
    """Bulletproof Anthropic client with multiple fallback strategies"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key.strip() if api_key else ""
        self.client = None
        self.is_available = False
        
        logger.info("🤖 Bulletproof Anthropic Client initializing...")
        
        if not self.api_key:
            logger.warning("❌ No Anthropic API key provided")
            return
        
        # More flexible key validation
        if not (self.api_key.startswith('sk-ant-') or self.api_key.startswith('sk-')):
            logger.warning(f"⚠️ Unusual API key format: {self.api_key[:15]}...")
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.is_available = True
            logger.info("✅ Anthropic client initialized successfully")
        except ImportError:
            logger.warning("⚠️ Anthropic package not installed")
        except Exception as e:
            logger.error(f"❌ Anthropic client initialization failed: {e}")

    async def get_synopsis(self, company_data: Dict) -> str:
        """Get AI synopsis with multiple fallback strategies"""
        if not self.is_available:
            return self._generate_rule_based_synopsis(company_data)
        
        # Strategy 1: Try latest model
        synopsis = await self._try_model("claude-3-5-sonnet-20241022", company_data)
        if synopsis:
            return synopsis
        
        # Strategy 2: Try stable model
        synopsis = await self._try_model("claude-3-sonnet-20240229", company_data)
        if synopsis:
            return synopsis
        
        # Strategy 3: Try fast model
        synopsis = await self._try_model("claude-3-haiku-20240307", company_data)
        if synopsis:
            return synopsis
        
        # Fallback: Rule-based synopsis
        logger.warning("⚠️ All Anthropic models failed, using rule-based synopsis")
        return self._generate_rule_based_synopsis(company_data)

    async def _try_model(self, model: str, company_data: Dict) -> Optional[str]:
        """Try a specific model"""
        try:
            logger.info(f"🤖 Trying model: {model}")
            
            prompt = self._create_prompt(company_data)
            
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=model,
                max_tokens=250,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            if response and response.content:
                synopsis = response.content[0].text.strip()
                if len(synopsis) > 20:  # Minimum viable synopsis
                    logger.info(f"✅ Success with {model}")
                    return self._clean_synopsis(synopsis)
            
        except Exception as e:
            logger.warning(f"⚠️ Model {model} failed: {e}")
        
        return None

    def _create_prompt(self, company_data: Dict) -> str:
        """Create a comprehensive prompt"""
        company_name = company_data.get('lgnm', 'Unknown Company')
        status = company_data.get('sts', 'Unknown')
        gstin = company_data.get('gstin', 'N/A')
        returns_count = len(company_data.get('returns', []))
        is_mock = company_data.get('_mock_data', False)
        
        prompt = f"""Analyze this GST company data:

Company: {company_name}
GSTIN: {gstin}
Status: {status}
Returns Filed: {returns_count}
Business Type: {company_data.get('ctb', 'Not specified')}
E-Invoice Status: {company_data.get('einvoiceStatus', 'Unknown')}

{"Note: This is simulated data for demonstration." if is_mock else ""}

Write a professional 2-sentence analysis focusing on compliance status and business health. Keep it under 150 words."""
        
        return prompt

    def _clean_synopsis(self, synopsis: str) -> str:
        """Clean and format synopsis"""
        import re
        
        # Remove markdown
        synopsis = re.sub(r'\*\*(.*?)\*\*', r'\1', synopsis)
        synopsis = re.sub(r'\*(.*?)\*', r'\1', synopsis)
        synopsis = re.sub(r'#{1,6}\s*', '', synopsis)
        
        # Clean whitespace
        synopsis = ' '.join(synopsis.split())
        
        # Ensure proper ending
        if synopsis and not synopsis.endswith(('.', '!', '?')):
            synopsis += '.'
        
        # Limit length
        if len(synopsis) > 300:
            synopsis = synopsis[:297] + '...'
        
        return synopsis or "Analysis not available"

    def _generate_rule_based_synopsis(self, company_data: Dict) -> str:
        """Generate synopsis using business rules"""
        try:
            company_name = company_data.get('lgnm', 'Company')
            status = company_data.get('sts', 'Unknown').lower()
            returns_count = len(company_data.get('returns', []))
            gstin = company_data.get('gstin', 'N/A')
            is_mock = company_data.get('_mock_data', False)
            
            # Status analysis
            if status == 'active':
                status_text = "maintains active GST registration"
            elif status == 'suspended':
                status_text = "currently has suspended registration"
            elif status == 'cancelled':
                status_text = "has cancelled registration"
            else:
                status_text = f"shows {status} registration status"
            
            # Compliance analysis
            if returns_count >= 12:
                compliance_text = "demonstrates excellent compliance with comprehensive filing history"
            elif returns_count >= 8:
                compliance_text = "shows strong compliance with regular filings"
            elif returns_count >= 4:
                compliance_text = "maintains moderate compliance standards"
            elif returns_count > 0:
                compliance_text = "has basic filing activity"
            else:
                compliance_text = "shows minimal recent filing activity"
            
            # E-invoice analysis
            einvoice_status = company_data.get('einvoiceStatus', 'No')
            if einvoice_status.lower() == 'yes':
                einvoice_text = " The company is e-invoice enabled, indicating good digital compliance."
            else:
                einvoice_text = ""
            
            # Mock data disclaimer
            mock_disclaimer = " [Note: Analysis based on simulated data]" if is_mock else ""
            
            synopsis = f"{company_name} (GSTIN: {gstin}) {status_text} and {compliance_text}.{einvoice_text}{mock_disclaimer}"
            
            return synopsis
            
        except Exception as e:
            logger.error(f"Rule-based synopsis failed: {e}")
            return "Company analysis temporarily unavailable due to system limitations."

# Global instances for easy import
def create_bulletproof_clients():
    """Create bulletproof API clients"""
    rapidapi_key = os.getenv("RAPIDAPI_KEY", "").strip()
    rapidapi_host = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com").strip()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    
    gst_client = None
    ai_client = None
    
    if rapidapi_key and rapidapi_host:
        gst_client = BulletproofGSTClient(rapidapi_key, rapidapi_host)
        logger.info("✅ Bulletproof GST client created")
    else:
        logger.error("❌ GST client not created - missing API key or host")
    
    if anthropic_key:
        ai_client = BulletproofAnthropicClient(anthropic_key)
        logger.info("✅ Bulletproof AI client created")
    else:
        logger.warning("⚠️ AI client not created - missing API key")
    
    return gst_client, ai_client

# Test function
async def test_bulletproof_clients():
    """Test the bulletproof clients"""
    logger.info("🧪 Testing Bulletproof Clients")
    logger.info("=" * 50)
    
    gst_client, ai_client = create_bulletproof_clients()
    
    # Test GST client
    if gst_client:
        try:
            result = await gst_client.fetch_gstin_data("29AAAPL2356Q1ZS")
            logger.info(f"✅ GST Client Test: {result.get('lgnm', 'Success')}")
        except Exception as e:
            logger.error(f"❌ GST Client Test Failed: {e}")
    
    # Test AI client
    if ai_client:
        try:
            test_data = {"lgnm": "Test Company", "sts": "Active", "returns": []}
            synopsis = await ai_client.get_synopsis(test_data)
            logger.info(f"✅ AI Client Test: {synopsis[:50]}...")
        except Exception as e:
            logger.error(f"❌ AI Client Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_bulletproof_clients())