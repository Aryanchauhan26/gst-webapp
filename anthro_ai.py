#!/usr/bin/env python3
"""
Anthropic AI Integration for GST Intelligence Platform - FIXED VERSION
Enhanced with robust error handling, fallbacks, and better caching
"""

import os
import json
import logging
import asyncio
import hashlib
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Anthropic - handle gracefully if not available
try:
    import anthropic
    HAS_ANTHROPIC = True
    logger.info("✅ Anthropic package imported successfully")
except ImportError:
    HAS_ANTHROPIC = False
    anthropic = None
    logger.warning("⚠️ Anthropic package not available - AI features will use fallbacks")

class AIAnalysisError(Exception):
    """Custom exception for AI analysis errors."""
    pass

class AnthropicAIClient:
    """
    Enhanced Anthropic AI client with robust error handling and caching.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        self.is_available = False
        self.last_error = None
        self.request_count = 0
        self.error_count = 0

        # Rate limiting
        self.rate_limit_per_minute = 45  # Conservative limit
        self.request_history = []

        # Cache for responses
        self.response_cache = {}
        self.cache_ttl = 3600  # 1 hour

        # Fallback configurations
        self.fallback_enabled = True
        self.max_retries = 3
        self.retry_delay = 2  # seconds

        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Anthropic client with enhanced error handling."""
        if not HAS_ANTHROPIC:
            logger.warning("❌ Anthropic package not installed. Using fallback mode.")
            self.is_available = False
            return

        if not self.api_key:
            logger.warning("❌ ANTHROPIC_API_KEY not configured. Using fallback mode.")
            self.is_available = False
            return

        # Validate API key format
        if not self.api_key.startswith('sk-ant-'):
            logger.warning("❌ Invalid ANTHROPIC_API_KEY format. Using fallback mode.")
            self.is_available = False
            return

        try:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.is_available = True
            logger.info("✅ Anthropic AI client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Anthropic client: {e}")
            self.last_error = str(e)
            self.is_available = False

    def _is_rate_limited(self) -> bool:
        """Check if we're hitting rate limits."""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)

        # Clean old requests
        self.request_history = [
            req_time for req_time in self.request_history 
            if req_time > minute_ago
        ]

        return len(self.request_history) >= self.rate_limit_per_minute

    def _get_cache_key(self, company_data: Dict) -> str:
        """Generate a cache key for company data."""
        # Include key fields that affect analysis
        key_fields = {
            'gstin': company_data.get('gstin', ''),
            'business_status': company_data.get('business_status', ''),
            'filing_status': company_data.get('filing_status', ''),
            'last_return_filed': company_data.get('last_return_filed', ''),
            'compliance_score': company_data.get('compliance_score', 0)
        }
        
        # Create hash from sorted key fields
        key_string = json.dumps(key_fields, sort_keys=True)
        return f"synopsis_{hashlib.md5(key_string.encode()).hexdigest()}"

    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid."""
        if not cache_entry:
            return False
        
        cached_time = cache_entry.get('timestamp', 0)
        return (datetime.now().timestamp() - cached_time) < self.cache_ttl

    def _create_prompt(self, company_data: Dict) -> str:
        """Create a comprehensive prompt for AI analysis."""
        # Extract key information with safe defaults
        gstin = company_data.get('gstin', 'Unknown')
        company_name = company_data.get('legal_name', 
                                      company_data.get('trade_name', 'Unknown Company'))
        business_status = company_data.get('business_status', 'Unknown')
        filing_status = company_data.get('filing_status', 'Unknown')
        compliance_score = company_data.get('compliance_score', 0)
        registration_date = company_data.get('registration_date', 'Unknown')
        last_return_filed = company_data.get('last_return_filed', 'Unknown')
        state = company_data.get('state', 'Unknown')
        business_type = company_data.get('business_type', 'Unknown')
        annual_turnover = company_data.get('annual_turnover', 'Unknown')

        prompt = f"""
        You are an expert GST compliance analyst. Analyze the following company data and provide a professional synopsis focusing on compliance health, business status, and key insights.

        Company Information:
        - GSTIN: {gstin}
        - Company Name: {company_name}
        - Business Status: {business_status}
        - Filing Status: {filing_status}
        - Registration Date: {registration_date}
        - Last Return Filed: {last_return_filed}
        - Compliance Score: {compliance_score}%
        - State: {state}
        - Business Type: {business_type}
        - Annual Turnover: {annual_turnover}

        Analysis Requirements:
        1. Assess overall compliance health based on filing status and compliance score
        2. Identify any red flags or concerns about business operations
        3. Provide actionable insights or recommendations
        4. Maintain a professional, factual tone
        5. Keep response under 200 words

        Provide only the analysis text without additional formatting or headers.
        """

        return prompt.strip()

    async def _make_api_request(self, prompt: str) -> Optional[str]:
        """Make API request with retry logic and better error handling."""
        if not self.is_available:
            raise AIAnalysisError("AI service not available")

        if self._is_rate_limited():
            raise AIAnalysisError("Rate limit exceeded")

        # Record request
        self.request_history.append(datetime.now())
        self.request_count += 1

        for attempt in range(self.max_retries):
            try:
                response = await asyncio.to_thread(
                    self.client.messages.create,
                    model="claude-3-haiku-20240307",  # Use more cost-effective model
                    max_tokens=250,
                    temperature=0.3,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                if response and response.content:
                    return response.content[0].text if response.content else None

            except anthropic.APIError as e:
                logger.error(f"Anthropic API error (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    raise AIAnalysisError(f"API error after {self.max_retries} attempts: {e}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                
            except anthropic.RateLimitError as e:
                logger.warning(f"Rate limit hit (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    raise AIAnalysisError("Rate limit exceeded")
                await asyncio.sleep(self.retry_delay * (attempt + 1) * 2)
                
            except Exception as e:
                logger.error(f"Unexpected error in AI request (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    self.error_count += 1
                    raise AIAnalysisError(f"Request failed after {self.max_retries} attempts: {e}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        return None

    def _extract_synopsis(self, response: str) -> str:
        """Extract and clean the synopsis from AI response."""
        if not response:
            return "Analysis not available"

        # Clean up the response
        synopsis = response.strip()

        # Remove any markdown formatting
        synopsis = re.sub(r'\*\*(.*?)\*\*', r'\1', synopsis)  # Bold
        synopsis = re.sub(r'\*(.*?)\*', r'\1', synopsis)      # Italic
        synopsis = re.sub(r'#{1,6}\s*', '', synopsis)         # Headers
        synopsis = re.sub(r'```.*?```', '', synopsis, flags=re.DOTALL)  # Code blocks

        # Remove extra whitespace
        synopsis = re.sub(r'\s+', ' ', synopsis)

        # Ensure it ends with proper punctuation
        if synopsis and not synopsis.endswith(('.', '!', '?')):
            synopsis += '.'

        # Truncate if too long
        if len(synopsis) > 300:
            synopsis = synopsis[:297] + '...'

        return synopsis or "Unable to generate analysis"

    async def get_synopsis(self, company_data: Dict) -> Optional[str]:
        """
        Generate AI-powered synopsis with comprehensive error handling.
        
        Args:
            company_data: Dictionary containing GST company data
            
        Returns:
            AI-generated synopsis string or None if failed
        """
        if not company_data:
            logger.warning("No company data provided for AI analysis")
            return None

        try:
            # Check cache first
            cache_key = self._get_cache_key(company_data)
            if cache_key in self.response_cache:
                cache_entry = self.response_cache[cache_key]
                if self._is_cache_valid(cache_entry):
                    logger.info("Returning cached AI synopsis")
                    return cache_entry['synopsis']

            # Try AI analysis
            if self.is_available:
                prompt = self._create_prompt(company_data)
                response = await self._make_api_request(prompt)
                
                if response:
                    synopsis = self._extract_synopsis(response)
                    
                    # Cache the result
                    self.response_cache[cache_key] = {
                        'synopsis': synopsis,
                        'timestamp': datetime.now().timestamp()
                    }
                    
                    logger.info("AI synopsis generated successfully")
                    return synopsis

        except AIAnalysisError as e:
            logger.error(f"AI analysis failed: {e}")
            self.last_error = str(e)
            self.error_count += 1
            
        except Exception as e:
            logger.error(f"Unexpected error in AI synopsis generation: {e}")
            self.last_error = str(e)
            self.error_count += 1

        # Return fallback if AI fails
        if self.fallback_enabled:
            logger.info("Using fallback synopsis generation")
            return generate_fallback_synopsis(company_data)

        return None

    def get_health_status(self) -> Dict[str, Any]:
        """Get the health status of the AI client."""
        return {
            'available': self.is_available,
            'has_api_key': bool(self.api_key),
            'has_anthropic_package': HAS_ANTHROPIC,
            'request_count': self.request_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(self.request_count, 1),
            'last_error': self.last_error,
            'cache_entries': len(self.response_cache),
            'rate_limited': self._is_rate_limited(),
            'fallback_enabled': self.fallback_enabled
        }

    def clear_cache(self):
        """Clear the response cache."""
        self.response_cache.clear()
        logger.info("AI response cache cleared")

    def reset_errors(self):
        """Reset error counters."""
        self.error_count = 0
        self.last_error = None
        logger.info("AI error counters reset")

# Global AI client instance
_ai_client = None

def get_ai_client() -> AnthropicAIClient:
    """Get or create the global AI client instance."""
    global _ai_client
    if _ai_client is None:
        _ai_client = AnthropicAIClient()
    return _ai_client

async def get_anthropic_synopsis(company_data: Dict) -> Optional[str]:
    """
    Public function to get AI synopsis with fallback.

    Args:
        company_data: Dictionary containing GST company data

    Returns:
        AI-generated synopsis string or fallback analysis
    """
    if not company_data:
        logger.warning("No company data provided for AI analysis")
        return generate_fallback_synopsis(company_data)

    try:
        client = get_ai_client()
        synopsis = await client.get_synopsis(company_data)
        
        # Always return something useful
        if synopsis:
            return synopsis
        else:
            logger.warning("AI synopsis generation failed, using fallback")
            return generate_fallback_synopsis(company_data)
            
    except Exception as e:
        logger.error(f"Error in get_anthropic_synopsis: {e}")
        return generate_fallback_synopsis(company_data)

def generate_fallback_synopsis(company_data: Dict) -> str:
    """
    Generate a comprehensive fallback synopsis when AI is not available.

    Args:
        company_data: Dictionary containing GST company data

    Returns:
        Structured analysis string
    """
    try:
        # Extract key information with safe defaults
        company_name = company_data.get('legal_name', 
                                      company_data.get('trade_name', 'Company'))
        gstin = company_data.get('gstin', 'Unknown')
        business_status = company_data.get('business_status', 'Unknown')
        filing_status = company_data.get('filing_status', 'Unknown')
        compliance_score = company_data.get('compliance_score', 0)
        last_return_filed = company_data.get('last_return_filed', 'Unknown')

        # Determine compliance health
        if compliance_score >= 85:
            health = "excellent"
            health_desc = "demonstrates exceptional compliance standards"
        elif compliance_score >= 70:
            health = "good"
            health_desc = "maintains good compliance practices"
        elif compliance_score >= 50:
            health = "average"
            health_desc = "shows moderate compliance performance"
        else:
            health = "concerning"
            health_desc = "requires immediate attention for compliance issues"

        # Business status analysis
        if business_status.lower() == "active":
            status_desc = "The company maintains active registration status"
        elif business_status.lower() == "suspended":
            status_desc = "The company registration is currently suspended"
        elif business_status.lower() == "cancelled":
            status_desc = "The company registration has been cancelled"
        else:
            status_desc = f"The company status is {business_status.lower()}"

        # Filing status analysis
        if filing_status.lower() == "regular":
            filing_desc = "with consistent filing patterns"
        elif filing_status.lower() == "irregular":
            filing_desc = "but shows irregular filing behavior"
        elif filing_status.lower() == "non-filer":
            filing_desc = "with significant filing gaps"
        else:
            filing_desc = f"with {filing_status.lower()} filing status"

        # Recent activity analysis
        activity_desc = ""
        if last_return_filed and last_return_filed != 'Unknown':
            try:
                from datetime import datetime
                if isinstance(last_return_filed, str):
                    last_date = datetime.strptime(last_return_filed, '%Y-%m-%d')
                    days_ago = (datetime.now() - last_date).days
                    if days_ago <= 30:
                        activity_desc = "Recent filing activity indicates active compliance management."
                    elif days_ago <= 90:
                        activity_desc = "Filing activity is moderately recent."
                    else:
                        activity_desc = "Filing activity shows potential delays."
                else:
                    activity_desc = "Filing activity requires monitoring."
            except:
                activity_desc = "Filing timeline requires verification."

        # Construct comprehensive synopsis
        synopsis = f"{company_name} (GSTIN: {gstin}) {health_desc} with a compliance score of {compliance_score}%. {status_desc} {filing_desc}. {activity_desc}"

        # Add recommendations based on score
        if compliance_score < 50:
            synopsis += " Immediate review of compliance procedures is recommended."
        elif compliance_score < 70:
            synopsis += " Enhanced monitoring and compliance improvements are advisable."
        else:
            synopsis += " The company demonstrates reliable compliance practices."

        return synopsis.strip()

    except Exception as e:
        logger.error(f"Fallback synopsis generation failed: {e}")
        return "GST compliance analysis is temporarily unavailable. Please try again later."

def get_ai_health() -> Dict[str, Any]:
    """Get AI service health information."""
    client = get_ai_client()
    return client.get_health_status()

def clear_ai_cache():
    """Clear the AI response cache."""
    client = get_ai_client()
    client.clear_cache()

def reset_ai_errors():
    """Reset AI error counters."""
    client = get_ai_client()
    client.reset_errors()

# Enhanced analysis functions
async def get_compliance_insights(company_data: Dict) -> Dict[str, Any]:
    """
    Get comprehensive compliance insights with both AI and rule-based analysis.

    Args:
        company_data: Dictionary containing GST company data

    Returns:
        Dictionary with various insights
    """
    insights = {
        'ai_synopsis': None,
        'fallback_synopsis': None,
        'risk_factors': [],
        'positive_indicators': [],
        'recommendations': [],
        'compliance_trend': 'stable',
        'risk_level': 'medium'
    }

    try:
        # Try to get AI synopsis
        ai_synopsis = await get_anthropic_synopsis(company_data)
        insights['ai_synopsis'] = ai_synopsis

        # Always generate fallback for comparison
        insights['fallback_synopsis'] = generate_fallback_synopsis(company_data)

        # Analyze risk factors
        insights['risk_factors'] = _analyze_risk_factors(company_data)
        insights['positive_indicators'] = _analyze_positive_indicators(company_data)
        insights['recommendations'] = _generate_recommendations(company_data)
        insights['compliance_trend'] = _assess_compliance_trend(company_data)
        insights['risk_level'] = _assess_risk_level(company_data)

    except Exception as e:
        logger.error(f"Compliance insights generation failed: {e}")
        insights['error'] = str(e)

    return insights

def _analyze_risk_factors(company_data: Dict) -> List[str]:
    """Analyze potential risk factors."""
    risks = []

    business_status = company_data.get('business_status', '').lower()
    filing_status = company_data.get('filing_status', '').lower()
    compliance_score = company_data.get('compliance_score', 0)

    if business_status not in ['active', 'registered']:
        risks.append(f"Business status is {business_status}")

    if 'irregular' in filing_status or 'non-filer' in filing_status:
        risks.append("Irregular filing pattern detected")

    if compliance_score < 40:
        risks.append("Very low compliance score indicates significant issues")
    elif compliance_score < 60:
        risks.append("Below-average compliance performance")

    # Check for outdated filings
    last_filed = company_data.get('last_return_filed')
    if last_filed and last_filed != 'Unknown':
        try:
            from datetime import datetime
            if isinstance(last_filed, str):
                last_date = datetime.strptime(last_filed, '%Y-%m-%d')
                days_ago = (datetime.now() - last_date).days
                if days_ago > 90:
                    risks.append("Returns not filed recently")
        except:
            pass

    return risks

def _analyze_positive_indicators(company_data: Dict) -> List[str]:
    """Analyze positive compliance indicators."""
    positives = []

    business_status = company_data.get('business_status', '').lower()
    filing_status = company_data.get('filing_status', '').lower()
    compliance_score = company_data.get('compliance_score', 0)

    if business_status == 'active':
        positives.append("Active business registration status")

    if filing_status == 'regular':
        positives.append("Regular filing compliance")

    if compliance_score >= 80:
        positives.append("High compliance score demonstrates strong practices")
    elif compliance_score >= 60:
        positives.append("Acceptable compliance performance")

    # Check for recent filings
    last_filed = company_data.get('last_return_filed')
    if last_filed and last_filed != 'Unknown':
        try:
            from datetime import datetime
            if isinstance(last_filed, str):
                last_date = datetime.strptime(last_filed, '%Y-%m-%d')
                days_ago = (datetime.now() - last_date).days
                if days_ago <= 30:
                    positives.append("Recent filing activity")
        except:
            pass

    return positives

def _generate_recommendations(company_data: Dict) -> List[str]:
    """Generate actionable recommendations."""
    recommendations = []

    compliance_score = company_data.get('compliance_score', 0)
    filing_status = company_data.get('filing_status', '').lower()
    business_status = company_data.get('business_status', '').lower()

    if compliance_score < 50:
        recommendations.append("Immediate compliance review and corrective action required")
    elif compliance_score < 70:
        recommendations.append("Implement enhanced compliance monitoring procedures")

    if 'irregular' in filing_status:
        recommendations.append("Establish regular filing schedule and monitoring")

    if business_status != 'active':
        recommendations.append("Address business registration status issues")

    if not recommendations:
        recommendations.append("Maintain current compliance practices")

    return recommendations

def _assess_compliance_trend(company_data: Dict) -> str:
    """Assess compliance trend."""
    compliance_score = company_data.get('compliance_score', 0)
    filing_status = company_data.get('filing_status', '').lower()

    if compliance_score >= 80 and 'regular' in filing_status:
        return 'improving'
    elif compliance_score >= 60:
        return 'stable'
    else:
        return 'declining'

def _assess_risk_level(company_data: Dict) -> str:
    """Assess overall risk level."""
    compliance_score = company_data.get('compliance_score', 0)
    business_status = company_data.get('business_status', '').lower()
    filing_status = company_data.get('filing_status', '').lower()

    if compliance_score < 40 or business_status != 'active' or 'non-filer' in filing_status:
        return 'high'
    elif compliance_score < 70 or 'irregular' in filing_status:
        return 'medium'
    else:
        return 'low'

# Export functions
__all__ = [
    'get_anthropic_synopsis',
    'get_ai_health',
    'clear_ai_cache',
    'reset_ai_errors',
    'generate_fallback_synopsis',
    'get_compliance_insights',
    'AnthropicAIClient',
    'AIAnalysisError'
]

# Test functionality
if __name__ == "__main__":
    async def test_ai():
        """Test the AI functionality."""
        test_data = {
            'gstin': '29AAAPL2356Q1ZS',
            'legal_name': 'Test Company Pvt Ltd',
            'business_status': 'Active',
            'filing_status': 'Regular',
            'compliance_score': 85,
            'registration_date': '2020-01-15',
            'last_return_filed': '2024-01-15'
        }

        print("🧪 Testing AI Synopsis Generation...")
        print("=" * 50)

        # Test AI synopsis
        synopsis = await get_anthropic_synopsis(test_data)
        print(f"📝 AI Synopsis: {synopsis}")

        # Test fallback
        fallback = generate_fallback_synopsis(test_data)
        print(f"📝 Fallback Synopsis: {fallback}")

        # Test health
        health = get_ai_health()
        print(f"🏥 AI Health Status:")
        for key, value in health.items():
            print(f"  {key}: {value}")

        # Test insights
        insights = await get_compliance_insights(test_data)
        print(f"💡 Compliance Insights:")
        for key, value in insights.items():
            if isinstance(value, list):
                print(f"  {key}: {', '.join(value) if value else 'None'}")
            else:
                print(f"  {key}: {value}")

        print("=" * 50)
        print("✅ AI testing completed")

    # Run test
    asyncio.run(test_ai())