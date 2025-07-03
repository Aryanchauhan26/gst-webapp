# Enhanced AI module with better error handling
import os
import asyncio
import httpx
import logging
from typing import Dict, Optional
import anthropic
from datetime import datetime

logger = logging.getLogger(__name__)

class CompanyIntelligence:
    def __init__(self, anthropic_api_key: str = None):
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        
        if self.api_key and self.api_key.strip():
            try:
                # Validate API key format
                if not self.api_key.startswith('sk-ant-api'):
                    logger.warning("⚠️ Anthropic API key format appears invalid")
                    
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("✅ Anthropic AI client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Anthropic client: {e}")
                self.client = None
        else:
            logger.warning("⚠️ ANTHROPIC_API_KEY not configured - AI features disabled")

    async def get_company_synopsis(self, company_data: Dict, compliance_score: float) -> Optional[str]:
        """Generate comprehensive company synopsis with fallback."""
        if not self.client:
            logger.warning("AI client not available, using fallback synopsis")
            return self.generate_fallback_synopsis(company_data, compliance_score)

        try:
            company_name = company_data.get("lgnm", "Unknown Company")
            gstin = company_data.get("gstin", "")
            
            # Create prompt for AI analysis
            prompt = self.create_analysis_prompt(company_data, compliance_score, company_name, gstin)
            
            # Make API request with timeout and retries
            synopsis = await self.make_ai_request(prompt)
            
            if synopsis:
                logger.info(f"✅ AI synopsis generated for {company_name}")
                return synopsis
            else:
                logger.warning(f"⚠️ Empty AI response for {company_name}")
                return self.generate_fallback_synopsis(company_data, compliance_score)
                
        except Exception as e:
            logger.error(f"❌ AI synopsis generation failed: {e}")
            return self.generate_fallback_synopsis(company_data, compliance_score)

    async def make_ai_request(self, prompt: str, max_retries: int = 2) -> Optional[str]:
        """Make AI request with proper error handling and retries."""
        for attempt in range(max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self.client.messages.create(
                            model="claude-3-sonnet-20240229",
                            max_tokens=500,
                            temperature=0.7,
                            messages=[{"role": "user", "content": prompt}]
                        )
                    ),
                    timeout=30.0  # 30 second timeout
                )
                
                if response and response.content:
                    return response.content[0].text.strip()
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏰ AI request timeout (attempt {attempt + 1})")
            except anthropic.AuthenticationError as e:
                logger.error(f"🔑 AI authentication failed: {e}")
                logger.error("Please check your ANTHROPIC_API_KEY in environment variables")
                break  # Don't retry auth errors
            except anthropic.RateLimitError as e:
                logger.warning(f"⏱️ AI rate limit hit (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"❌ AI request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(1)
        
        return None

    def create_analysis_prompt(self, company_data: Dict, compliance_score: float, company_name: str, gstin: str) -> str:
        """Create optimized prompt for AI analysis."""
        return f"""
Analyze this Indian company's GST data and provide a concise business synopsis:

Company: {company_name}
GSTIN: {gstin}
Compliance Score: {compliance_score}%
Registration Date: {company_data.get('rgdt', 'Not available')}
Business Type: {company_data.get('ctb', 'Not specified')}
State: {company_data.get('stj', 'Not available')}

Provide a 2-3 sentence business synopsis focusing on:
1. Company's compliance standing
2. Business stability indicators
3. Key operational insights

Keep it professional, factual, and under 150 words.
"""

    def generate_fallback_synopsis(self, company_data: Dict, compliance_score: float) -> str:
        """Generate fallback synopsis when AI is unavailable."""
        company_name = company_data.get("lgnm", "This company")
        business_type = company_data.get("ctb", "business entity")
        state = company_data.get("stj", "India")
        
        compliance_text = "excellent" if compliance_score >= 85 else \
                         "good" if compliance_score >= 70 else \
                         "moderate" if compliance_score >= 55 else "concerning"
        
        return f"{company_name} is a {business_type} registered in {state} with a compliance score of {compliance_score}%. " \
               f"The company demonstrates {compliance_text} GST compliance practices. " \
               f"{'This indicates strong regulatory adherence and operational stability.' if compliance_score >= 70 else 'There may be opportunities for improving compliance management.'}"

# Backward compatibility function
async def get_anthropic_synopsis(company_data: Dict, compliance_score: float) -> Optional[str]:
    """Main function for generating company synopsis."""
    intelligence = CompanyIntelligence()
    return await intelligence.get_company_synopsis(company_data, compliance_score)