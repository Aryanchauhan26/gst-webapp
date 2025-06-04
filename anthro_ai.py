# Fixed anthro_ai.py - Focus on company business overview
import os
import httpx
from bs4 import BeautifulSoup
import asyncio
from typing import Dict, List, Optional
import re
import time
import logging

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_anthropic_synopsis(company_data: Dict) -> Optional[str]:
    """
    Generate a business overview using Anthropic Claude AI.
    Returns a string synopsis or None if not available.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not AsyncAnthropic:
        logger.warning("Anthropic API not configured or anthropic package not installed.")
        return None

    prompt = (
        f"Company Name: {company_data.get('lgnm', 'N/A')}\n"
        f"Business Type: {company_data.get('ctb', 'N/A')}\n"
        f"Trade Name: {company_data.get('tradeName', 'N/A')}\n"
        f"Describe in 2-3 lines what this company does, based on the above."
    )
    try:
        client = AsyncAnthropic(api_key=api_key)
        response = await client.completions.create(
            model="claude-3-haiku-20240307",
            prompt=prompt,
            max_tokens=100,
            temperature=0.5,
        )
        return response.completion.strip()
    except Exception as e:
        logger.error(f"Anthropic AI error: {e}")
        return None

class EnhancedAnthropicSynopsis:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def search_company_info(self, company_name: str, gstin: str) -> Dict:
        """Search web for company business information with rate limiting"""
        search_results = {}
        
        # Clean company name for search
        clean_name = re.sub(r'\s*(PRIVATE|PVT|LIMITED|LTD)\.?\s*', '', company_name, flags=re.I).strip()
        
        # Focus on business-related searches
        search_queries = [
            f'"{clean_name}" company profile products services India',
            f'"{clean_name}" business overview achievements',
            f'"{clean_name}" what does company do industry',
            f'"about {clean_name}" company India business',
            f'site:linkedin.com/company "{clean_name}"',
            f'site:zaubacorp.com "{clean_name}"',
            f'"{clean_name}" annual report business activities'
        ]
        
        all_content = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for query in search_queries[:4]:  # Limit searches
                try:
                    # Rate limiting
                    await asyncio.sleep(1)
                    
                    # Use google search with error handling
                    try:
                        urls = list(search(query, num=3, stop=3, pause=2))
                    except Exception as e:
                        logger.warning(f"Search failed for query '{query}': {e}")
                        continue
                    
                    for url in urls[:2]:
                        try:
                            response = await client.get(url, headers=self.headers, timeout=5)
                            if response.status_code == 200:
                                soup = BeautifulSoup(response.text, 'html.parser')
                                
                                # Remove script and style elements
                                for script in soup(["script", "style", "nav", "footer"]):
                                    script.decompose()
                                
                                # Look for business-related content
                                business_keywords = ['about', 'products', 'services', 'business', 
                                                   'industry', 'solutions', 'offerings', 'overview',
                                                   'founded', 'established', 'specializes', 'provides']
                                
                                # Extract relevant paragraphs
                                relevant_text = []
                                for p in soup.find_all(['p', 'div', 'section']):
                                    text = p.get_text().strip()
                                    if text and len(text) > 50 and any(keyword in text.lower() for keyword in business_keywords):
                                        if clean_name.lower() in text.lower():
                                            relevant_text.append(text[:500])  # Limit each paragraph
                                
                                if relevant_text:
                                    content = f"Source: {url}\n"
                                    content += '\n'.join(relevant_text[:3])  # Top 3 relevant paragraphs
                                    all_content.append(content)
                                
                        except httpx.TimeoutException:
                            logger.warning(f"Timeout fetching {url}")
                            continue
                        except Exception as e:
                            logger.warning(f"Error fetching {url}: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Search error for query '{query}': {e}")
                    continue
        
        search_results['web_content'] = '\n\n'.join(all_content) if all_content else 'No additional information found online'
        return search_results

    async def get_enhanced_synopsis(self, company_data: dict) -> str:
        """Generate company business overview"""
        
        # Search for company business information
        try:
            web_data = await self.search_company_info(
                company_data.get("lgnm", ""),
                company_data.get("gstin", "")
            )
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            web_data = {'web_content': 'Web search unavailable'}
        
        # Prepare prompt focused on business overview
        enhanced_prompt = f"""
        You are a business analyst. Write a comprehensive business overview for this Indian company.
        
        COMPANY IDENTIFICATION:
        - Legal Name: {company_data.get("lgnm")}
        - Trade Name: {company_data.get("tradeName", "")}
        - GSTIN: {company_data.get("gstin")}
        - Type: {company_data.get("ctb", "")}
        - Registration: {company_data.get("rgdt", "")}
        - Location: {company_data.get("adr", "")}
        
        ADDITIONAL INFORMATION FROM WEB:
        {web_data.get('web_content', 'No additional information found')}
        
        INSTRUCTIONS:
        Write a 200-250 word business overview that includes:
        1. What the company does (products/services/industry)
        2. Key business activities and market focus
        3. Any notable achievements, certifications, or milestones found
        4. Company's market position or specializations
        5. Brief mention of compliance status (just 1 line at the end)
        
        Focus on the BUSINESS, not the GST data. If no specific business information is found,
        make intelligent inferences based on the company name and type.
        
        DO NOT just summarize GST filing data - describe what the actual company does.
        """
        
        try:
            message = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=512,
                temperature=0.7,
                messages=[{"role": "user", "content": enhanced_prompt}]
            )
            # Handle the response properly
            if hasattr(message, 'content') and len(message.content) > 0:
                return message.content[0].text.strip()
            else:
                raise ValueError("Invalid response from Anthropic API")
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            # Fallback synopsis focused on business
            return self.generate_fallback_business_synopsis(company_data)
    
    def generate_fallback_business_synopsis(self, company_data: dict) -> str:
        """Generate business-focused synopsis without API"""
        company_name = company_data.get("lgnm", "Unknown Company")
        company_type = company_data.get("ctb", "")
        location = company_data.get("adr", "")
        reg_date = company_data.get("rgdt", "")
        
        # Try to infer business from name
        name_lower = company_name.lower()
        
        if any(word in name_lower for word in ['tech', 'software', 'infotech', 'solutions', 'digital']):
            business_type = "technology and software solutions"
        elif any(word in name_lower for word in ['trading', 'exports', 'imports', 'international']):
            business_type = "trading and import/export"
        elif any(word in name_lower for word in ['manufacturing', 'industries', 'products', 'engineering']):
            business_type = "manufacturing"
        elif any(word in name_lower for word in ['services', 'consultancy', 'consulting', 'advisory']):
            business_type = "professional services"
        elif any(word in name_lower for word in ['pharma', 'medical', 'healthcare']):
            business_type = "healthcare and pharmaceutical"
        elif any(word in name_lower for word in ['retail', 'mart', 'store', 'bazaar']):
            business_type = "retail and distribution"
        else:
            business_type = "business operations"
        
        # Extract location details
        location_parts = location.split(',') if location else []
        city = location_parts[0].strip() if location_parts else 'India'
        
        # Build comprehensive synopsis
        synopsis = f"{company_name} is a {company_type} engaged in {business_type}. "
        
        if reg_date:
            try:
                year = reg_date.split('/')[-1]
                synopsis += f"Established in {year}, the company has been operational for several years. "
            except:
                pass
        
        synopsis += f"The company operates from {city}, serving clients across the region. "
        synopsis += "While specific details about the company's products, services, and market position "
        synopsis += "require further research, the company maintains its GST registration and "
        synopsis += "compliance obligations as per Indian tax regulations. "
        synopsis += f"As a {company_type}, the company likely focuses on {business_type} "
        synopsis += "activities in line with industry standards and regulatory requirements."
        
        return synopsis