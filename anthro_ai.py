#!/usr/bin/env python3
"""
Anthropic AI Integration for GST Intelligence Platform
Enhanced with comprehensive error handling and fallbacks
"""

import os
import json
import logging
import asyncio
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import re

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    anthropic = None

# Configure logging
logger = logging.getLogger(__name__)

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
        self.rate_limit_per_minute = 50
        self.request_history = []

        # Cache for responses
        self.response_cache = {}
        self.cache_ttl = 3600  # 1 hour

        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Anthropic client."""
        if not HAS_ANTHROPIC:
            logger.warning("Anthropic package not installed. AI features disabled.")
            return

        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not configured. AI features disabled.")
            return

        try:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.is_available = True
            logger.info("✅ Anthropic AI client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Anthropic client: {e}")
            self.last_error = str(e)

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
        gstin = company_data.get('gstin', '')
        # Include key fields that affect analysis
        key_fields = {
            'gstin': gstin,
            'business_status': company_data.get('business_status', ''),
            'filing_status': company_data.get('filing_status', ''),
            'last_return_filed': company_data.get('last_return_filed', ''),
            'compliance_score': company_data.get('compliance_score', 0)
        }
        return f"synopsis_{hash(json.dumps(key_fields, sort_keys=True))}"

    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid."""
        cached_time = cache_entry.get('timestamp', 0)
        return (datetime.now().timestamp() - cached_time) < self.cache_ttl

    async def get_synopsis(self, company_data: Dict) -> Optional[str]:
        """
        Generate AI-powered synopsis of company GST compliance.

        Args:
            company_data: Dictionary containing GST data

        Returns:
            String synopsis or None if unavailable
        """
        if not self.is_available:
            logger.debug("AI client not available")
            return None

        if self._is_rate_limited():
            logger.warning("Rate limit reached for AI requests")
            return None

        # Check cache first
        cache_key = self._get_cache_key(company_data)
        if cache_key in self.response_cache:
            cache_entry = self.response_cache[cache_key]
            if self._is_cache_valid(cache_entry):
                logger.debug("Using cached AI synopsis")
                return cache_entry['synopsis']
            else:
                # Remove expired cache entry
                del self.response_cache[cache_key]

        try:
            self.request_count += 1
            self.request_history.append(datetime.now())

            prompt = self._build_analysis_prompt(company_data)

            response = await self._make_api_request(prompt)

            if response:
                synopsis = self._extract_synopsis(response)

                # Cache the response
                self.response_cache[cache_key] = {
                    'synopsis': synopsis,
                    'timestamp': datetime.now().timestamp()
                }

                logger.info("✅ AI synopsis generated successfully")
                return synopsis

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"❌ AI synopsis generation failed: {e}")

        return None

    def _build_analysis_prompt(self, company_data: Dict) -> str:
        """Build the analysis prompt for the AI."""
        gstin = company_data.get('gstin', 'Unknown')
        company_name = company_data.get('legal_name', company_data.get('trade_name', 'Unknown Company'))
        business_status = company_data.get('business_status', 'Unknown')
        filing_status = company_data.get('filing_status', 'Unknown')
        registration_date = company_data.get('registration_date', 'Unknown')
        last_return_filed = company_data.get('last_return_filed', 'Unknown')
        compliance_score = company_data.get('compliance_score', 0)

        # Extract additional insights
        state = company_data.get('state', 'Unknown')
        business_type = company_data.get('business_type', 'Unknown')
        annual_turnover = company_data.get('annual_turnover', 'Unknown')

        prompt = f"""
        Analyze the following GST compliance data for a business and provide a concise, professional synopsis in 2-3 sentences.
        Focus on compliance status, business health, and any notable observations.

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

        Analysis Guidelines:
        1. Assess overall compliance health based on filing status and compliance score
        2. Note any concerns about irregular filing or business status issues
        3. Provide actionable insights or recommendations if applicable
        4. Keep the tone professional and factual
        5. Limit response to 150 words maximum

        Provide only the synopsis text, no additional formatting or headers.
        """

        return prompt.strip()

    async def _make_api_request(self, prompt: str) -> Optional[str]:
        """Make the actual API request to Anthropic."""
        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-sonnet-20240229",
                max_tokens=300,
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
            logger.error(f"Anthropic API error: {e}")
            raise AIAnalysisError(f"API error: {e}")
        except anthropic.RateLimitError as e:
            logger.warning(f"Anthropic rate limit hit: {e}")
            raise AIAnalysisError("Rate limit exceeded")
        except Exception as e:
            logger.error(f"Unexpected error in AI request: {e}")
            raise AIAnalysisError(f"Request failed: {e}")

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

        # Remove extra whitespace
        synopsis = re.sub(r'\s+', ' ', synopsis)

        # Ensure it ends with proper punctuation
        if synopsis and not synopsis.endswith(('.', '!', '?')):
            synopsis += '.'

        # Truncate if too long
        if len(synopsis) > 500:
            synopsis = synopsis[:497] + '...'

        return synopsis or "Unable to generate analysis"

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
            'rate_limited': self._is_rate_limited()
        }

    def clear_cache(self):
        """Clear the response cache."""
        self.response_cache.clear()
        logger.info("AI response cache cleared")

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
    Public function to get AI synopsis.

    Args:
        company_data: Dictionary containing GST company data

    Returns:
        AI-generated synopsis string or None
    """
    if not company_data:
        logger.warning("No company data provided for AI analysis")
        return None

    client = get_ai_client()
    return await client.get_synopsis(company_data)

def get_ai_health() -> Dict[str, Any]:
    """Get AI service health information."""
    client = get_ai_client()
    return client.get_health_status()

def clear_ai_cache():
    """Clear the AI response cache."""
    client = get_ai_client()
    client.clear_cache()

# Fallback analysis for when AI is not available
def generate_fallback_synopsis(company_data: Dict) -> str:
    """
    Generate a basic synopsis when AI is not available.

    Args:
        company_data: Dictionary containing GST company data

    Returns:
        Basic analysis string
    """
    try:
        company_name = company_data.get('legal_name', company_data.get('trade_name', 'Company'))
        gstin = company_data.get('gstin', 'Unknown')
        business_status = company_data.get('business_status', 'Unknown')
        filing_status = company_data.get('filing_status', 'Unknown')
        compliance_score = company_data.get('compliance_score', 0)

        # Basic analysis logic
        if compliance_score >= 80:
            health = "excellent"
        elif compliance_score >= 60:
            health = "good"
        elif compliance_score >= 40:
            health = "average"
        else:
            health = "poor"

        status_desc = ""
        if business_status == "Active" and filing_status == "Regular":
            status_desc = "The company maintains active status with regular filing compliance."
        elif business_status == "Active":
            status_desc = f"The company is active but shows {filing_status.lower()} filing patterns."
        else:
            status_desc = f"The company status is {business_status.lower()} with {filing_status.lower()} filing status."

        score_desc = f"Current compliance score of {compliance_score}% indicates {health} compliance health."

        return f"{company_name} (GSTIN: {gstin}) shows {health} GST compliance. {status_desc} {score_desc}"

    except Exception as e:
        logger.error(f"Fallback synopsis generation failed: {e}")
        return "Compliance analysis unavailable at this time."

# Enhanced analysis functions
async def get_compliance_insights(company_data: Dict) -> Dict[str, Any]:
    """
    Get comprehensive compliance insights.

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
        'compliance_trend': 'stable'
    }

    try:
        # Try to get AI synopsis
        ai_synopsis = await get_anthropic_synopsis(company_data)
        if ai_synopsis:
            insights['ai_synopsis'] = ai_synopsis

        # Always generate fallback
        insights['fallback_synopsis'] = generate_fallback_synopsis(company_data)

        # Analyze risk factors
        insights['risk_factors'] = _analyze_risk_factors(company_data)
        insights['positive_indicators'] = _analyze_positive_indicators(company_data)
        insights['recommendations'] = _generate_recommendations(company_data)
        insights['compliance_trend'] = _assess_compliance_trend(company_data)

    except Exception as e:
        logger.error(f"Compliance insights generation failed: {e}")

    return insights

def _analyze_risk_factors(company_data: Dict) -> List[str]:
    """Analyze potential risk factors."""
    risks = []

    business_status = company_data.get('business_status', '').lower()
    filing_status = company_data.get('filing_status', '').lower()
    compliance_score = company_data.get('compliance_score', 0)

    if business_status != 'active':
        risks.append(f"Business status is {business_status}")

    if 'irregular' in filing_status or 'non-filer' in filing_status:
        risks.append("Irregular filing pattern detected")

    if compliance_score < 40:
        risks.append("Low compliance score indicates significant issues")
    elif compliance_score < 60:
        risks.append("Below-average compliance score")

    # Check for outdated filings
    last_filed = company_data.get('last_return_filed')
    if last_filed:
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
        positives.append("Active business status")

    if 'regular' in filing_status:
        positives.append("Regular filing compliance")

    if compliance_score >= 80:
        positives.append("Excellent compliance score")
    elif compliance_score >= 70:
        positives.append("Good compliance score")

    return positives

def _generate_recommendations(company_data: Dict) -> List[str]:
    """Generate actionable recommendations."""
    recommendations = []

    filing_status = company_data.get('filing_status', '').lower()
    compliance_score = company_data.get('compliance_score', 0)

    if 'irregular' in filing_status:
        recommendations.append("Ensure timely filing of GST returns")

    if compliance_score < 60:
        recommendations.append("Review and improve compliance processes")

    if compliance_score < 80:
        recommendations.append("Regular monitoring of GST obligations recommended")

    return recommendations

def _assess_compliance_trend(company_data: Dict) -> str:
    """Assess the compliance trend."""
    compliance_score = company_data.get('compliance_score', 0)
    filing_status = company_data.get('filing_status', '').lower()

    if compliance_score >= 80 and 'regular' in filing_status:
        return 'improving'
    elif compliance_score >= 60:
        return 'stable'
    else:
        return 'declining'

# Batch processing for multiple companies
async def analyze_multiple_companies(companies_data: List[Dict]) -> List[Dict]:
    """
    Analyze multiple companies with rate limiting.

    Args:
        companies_data: List of company data dictionaries

    Returns:
        List of analysis results
    """
    results = []

    for i, company_data in enumerate(companies_data):
        try:
            # Add delay to respect rate limits
            if i > 0:
                await asyncio.sleep(1.2)  # ~50 requests per minute

            insights = await get_compliance_insights(company_data)
            results.append({
                'gstin': company_data.get('gstin'),
                'company_name': company_data.get('legal_name', company_data.get('trade_name')),
                'insights': insights,
                'processed_at': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Failed to analyze company {company_data.get('gstin')}: {e}")
            results.append({
                'gstin': company_data.get('gstin'),
                'company_name': company_data.get('legal_name', company_data.get('trade_name')),
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            })

    return results

# Export functions for backward compatibility
__all__ = [
    'get_anthropic_synopsis',
    'get_ai_health',
    'clear_ai_cache',
    'generate_fallback_synopsis',
    'get_compliance_insights',
    'analyze_multiple_companies',
    'AnthropicAIClient',
    'AIAnalysisError'
]

if __name__ == "__main__":
    # Test the AI functionality
    async def test_ai():
        test_data = {
            'gstin': '29AAAPL2356Q1ZS',
            'legal_name': 'Test Company Pvt Ltd',
            'business_status': 'Active',
            'filing_status': 'Regular',
            'compliance_score': 85,
            'registration_date': '2020-01-15',
            'last_return_filed': '2024-01-15'
        }

        print("Testing AI synopsis generation...")
        synopsis = await get_anthropic_synopsis(test_data)
        print(f"AI Synopsis: {synopsis}")

        print("\nTesting fallback synopsis...")
        fallback = generate_fallback_synopsis(test_data)
        print(f"Fallback Synopsis: {fallback}")

        print("\nAI Health Status:")
        health = get_ai_health()
        for key, value in health.items():
            print(f"  {key}: {value}")

    asyncio.run(test_ai())