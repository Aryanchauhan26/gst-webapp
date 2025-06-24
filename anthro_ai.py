#!/usr/bin/env python3
"""
Enhanced GST Company Analysis Module with AI Integration
Self-contained module for AI-powered company analysis and web scraping
Version: 2.0.0
"""

import os
import httpx
import asyncio
import re
import logging
import json
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Optional dependencies with graceful fallbacks
try:
    from bs4 import BeautifulSoup
    HAS_BEAUTIFULSOUP = True
except ImportError:
    logger.warning("BeautifulSoup not available - web scraping features disabled")
    HAS_BEAUTIFULSOUP = False

try:
    from googlesearch import search as google_search
    HAS_GOOGLE_SEARCH = True
except ImportError:
    logger.warning("Google search not available - falling back to DuckDuckGo only")
    HAS_GOOGLE_SEARCH = False

try:
    from anthropic import AsyncAnthropic
    HAS_ANTHROPIC = True
except ImportError:
    logger.warning("Anthropic SDK not available - AI features disabled")
    HAS_ANTHROPIC = False
    AsyncAnthropic = None


class CompanyAnalyzer:
    """
    Self-contained company analysis class with AI and web scraping capabilities
    """
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize the analyzer with optional AI capabilities"""
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.anthropic_client = None
        
        if self.anthropic_api_key and HAS_ANTHROPIC:
            try:
                self.anthropic_client = AsyncAnthropic(api_key=self.anthropic_api_key)
                logger.info("AI features enabled with Anthropic API")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
        
        # HTTP client configuration
        self.http_timeout = 10.0
        self.max_retries = 3
        self.user_agent = "GST-Intelligence-Platform/2.0 (Business Analysis Bot)"
        
        # Cache for reducing redundant requests
        self._cache = {}
        self._cache_ttl = timedelta(hours=1)
    
    async def search_company_web(self, company_name: str, location: str = None) -> List[str]:
        """
        Search for company information using multiple search engines
        Returns list of relevant URLs
        """
        if not HAS_BEAUTIFULSOUP:
            logger.warning("Web scraping disabled - BeautifulSoup not available")
            return []
        
        # Generate cache key
        cache_key = hashlib.md5(f"{company_name}_{location}".encode()).hexdigest()
        
        # Check cache first
        if cache_key in self._cache:
            cache_time, cached_result = self._cache[cache_key]
            if datetime.now() - cache_time < self._cache_ttl:
                logger.info(f"Using cached search results for {company_name}")
                return cached_result
        
        results = []
        clean_name = self._clean_company_name(company_name)
        
        # DuckDuckGo search (primary)
        duckduckgo_results = await self._search_duckduckgo(clean_name, location)
        results.extend(duckduckgo_results)
        
        # Google search (fallback if available)
        if HAS_GOOGLE_SEARCH and len(results) < 3:
            google_results = await self._search_google(clean_name, location)
            results.extend(google_results)
        
        # IndiaMART search (business directory)
        indiamart_results = await self._search_indiamart(clean_name)
        results.extend(indiamart_results)
        
        # Remove duplicates and limit results
        unique_results = list(dict.fromkeys(results))[:5]
        
        # Cache results
        self._cache[cache_key] = (datetime.now(), unique_results)
        
        logger.info(f"Found {len(unique_results)} URLs for {company_name}")
        return unique_results
    
    def _clean_company_name(self, company_name: str) -> str:
        """Clean company name for better search results"""
        # Remove common business suffixes
        suffixes = [
            r'\s*(PRIVATE|PVT|LIMITED|LTD|LLC|CORP|CORPORATION|INC|INCORPORATED)\.?\s*',
            r'\s*(COMPANY|CO|ENTERPRISES|INDUSTRIES|SERVICES|SOLUTIONS)\.?\s*'
        ]
        
        clean_name = company_name.strip()
        for suffix in suffixes:
            clean_name = re.sub(suffix, '', clean_name, flags=re.I)
        
        return clean_name.strip()
    
    async def _search_duckduckgo(self, company_name: str, location: str = None) -> List[str]:
        """Search using DuckDuckGo"""
        results = []
        
        # Build search queries
        queries = [
            f"{company_name} company profile India",
            f"{company_name} about us products services",
        ]
        
        if location:
            queries.append(f"{company_name} {location} company")
        
        async with httpx.AsyncClient(
            timeout=self.http_timeout,
            headers={'User-Agent': self.user_agent}
        ) as client:
            
            for query in queries[:2]:  # Limit to 2 queries to avoid rate limiting
                try:
                    response = await client.post(
                        "https://html.duckduckgo.com/html/",
                        data={"q": query, "t": "h_", "ia": "web"}
                    )
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        for result in soup.find_all('a', class_='result__a')[:3]:
                            url = result.get('href', '')
                            if self._is_valid_url(url):
                                results.append(url)
                    
                    # Rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"DuckDuckGo search error for '{query}': {e}")
                    continue
        
        return results
    
    async def _search_google(self, company_name: str, location: str = None) -> List[str]:
        """Search using Google (if available)"""
        if not HAS_GOOGLE_SEARCH:
            return []
        
        results = []
        
        try:
            query = f"{company_name} company India"
            if location:
                query += f" {location}"
            
            # Google search with rate limiting
            search_results = list(google_search(query, num=3, stop=3, pause=2))
            
            for url in search_results:
                if self._is_valid_url(url):
                    results.append(url)
                    
        except Exception as e:
            logger.warning(f"Google search failed: {e}")
        
        return results
    
    async def _search_indiamart(self, company_name: str) -> List[str]:
        """Search IndiaMART business directory"""
        results = []
        
        try:
            search_url = f"https://www.indiamart.com/search.html?ss={company_name.replace(' ', '+')}"
            
            async with httpx.AsyncClient(
                timeout=self.http_timeout,
                headers={'User-Agent': self.user_agent}
            ) as client:
                
                response = await client.get(search_url)
                
                if response.status_code == 200 and HAS_BEAUTIFULSOUP:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for company profile links
                    for link in soup.find_all('a', href=True)[:5]:
                        url = link.get('href', '')
                        if 'indiamart.com' in url and '/company/' in url:
                            if url.startswith('/'):
                                url = 'https://www.indiamart.com' + url
                            results.append(url)
                            
        except Exception as e:
            logger.warning(f"IndiaMART search error: {e}")
        
        return results
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate if URL is worth fetching"""
        if not url or len(url) < 10:
            return False
        
        # Skip irrelevant domains
        skip_domains = [
            'duckduckgo.com', 'google.com', 'facebook.com', 'twitter.com',
            'linkedin.com', 'youtube.com', 'instagram.com', 'amazon.com'
        ]
        
        for domain in skip_domains:
            if domain in url.lower():
                return False
        
        # Prefer business-relevant URLs
        if any(keyword in url.lower() for keyword in ['company', 'business', 'corporate', 'about']):
            return True
        
        return url.startswith('http') and '.' in url
    
    async def fetch_page_content(self, url: str) -> str:
        """
        Fetch and extract relevant content from a webpage
        Returns cleaned text content
        """
        if not HAS_BEAUTIFULSOUP:
            return ""
        
        try:
            async with httpx.AsyncClient(
                timeout=self.http_timeout,
                headers={'User-Agent': self.user_agent},
                follow_redirects=True
            ) as client:
                
                response = await client.get(url)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Remove unwanted elements
                    for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                        element.decompose()
                    
                    # Extract relevant content
                    content_tags = soup.find_all(['p', 'div', 'section', 'article'], limit=30)
                    relevant_content = []
                    
                    # Keywords that indicate business-relevant content
                    keywords = [
                        'about', 'company', 'business', 'service', 'product', 'solution',
                        'industry', 'founded', 'established', 'specialize', 'provide',
                        'offer', 'manufacture', 'expertise', 'mission', 'vision'
                    ]
                    
                    for tag in content_tags:
                        text = tag.get_text(strip=True)
                        if len(text) > 50 and any(kw in text.lower() for kw in keywords):
                            # Clean and truncate text
                            cleaned_text = re.sub(r'\s+', ' ', text)
                            relevant_content.append(cleaned_text[:500])
                            
                            if len(relevant_content) >= 5:
                                break
                    
                    return '\n\n'.join(relevant_content)
        
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e}")
        
        return ""
    
    async def get_company_info_from_web(self, company_name: str, gstin: str = None, location: str = None) -> Dict[str, Union[str, List[str]]]:
        """
        Gather comprehensive company information from web sources
        Returns dictionary with web content and sources
        """
        info = {
            'web_content': '',
            'sources': [],
            'summary': '',
            'keywords': []
        }
        
        try:
            # Search for company URLs
            urls = await self.search_company_web(company_name, location)
            
            if not urls:
                logger.info(f"No URLs found for {company_name}")
                return info
            
            # Fetch content from URLs
            all_content = []
            successful_sources = []
            
            for url in urls[:3]:  # Limit to top 3 URLs
                content = await self.fetch_page_content(url)
                if content and len(content) > 100:
                    all_content.append(f"Source: {url}\n{content}")
                    successful_sources.append(url)
                
                # Rate limiting
                await asyncio.sleep(0.5)
            
            if all_content:
                info['web_content'] = '\n\n---\n\n'.join(all_content)
                info['sources'] = successful_sources
                
                # Extract keywords
                keywords = self._extract_keywords(info['web_content'])
                info['keywords'] = keywords
                
                # Generate summary
                info['summary'] = self._generate_summary(info['web_content'])
            
            logger.info(f"Successfully gathered web info for {company_name} from {len(successful_sources)} sources")
            
        except Exception as e:
            logger.error(f"Web search error for {company_name}: {e}")
        
        return info
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract relevant keywords from content"""
        if not content:
            return []
        
        # Common business keywords
        business_keywords = [
            'manufacturing', 'services', 'consulting', 'technology', 'software',
            'healthcare', 'finance', 'retail', 'wholesale', 'trading', 'export',
            'import', 'logistics', 'construction', 'real estate', 'agriculture'
        ]
        
        content_lower = content.lower()
        found_keywords = []
        
        for keyword in business_keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)
        
        return found_keywords[:10]  # Limit to top 10
    
    def _generate_summary(self, content: str) -> str:
        """Generate a basic summary of the content"""
        if not content or len(content) < 100:
            return "Limited information available"
        
        # Extract first meaningful paragraph
        paragraphs = content.split('\n\n')
        
        for para in paragraphs:
            if len(para) > 100 and any(word in para.lower() for word in ['company', 'business', 'provide', 'service']):
                # Clean and truncate
                summary = re.sub(r'\s+', ' ', para).strip()
                return summary[:300] + "..." if len(summary) > 300 else summary
        
        # Fallback to first substantial paragraph
        for para in paragraphs:
            if len(para) > 100:
                summary = re.sub(r'\s+', ' ', para).strip()
                return summary[:300] + "..." if len(summary) > 300 else summary
        
        return "Company information available from web sources"
    
    async def get_anthropic_synopsis(self, company_data: Dict) -> Optional[str]:
        """
        Generate AI-powered business synopsis using web content + GST data
        """
        if not self.anthropic_client:
            logger.info("AI features not available - generating fallback synopsis")
            return await self._generate_fallback_synopsis(company_data)
        
        try:
            # Extract key information
            company_name = company_data.get('lgnm', 'Unknown Company')
            nba = company_data.get('nba', [])
            business_activities = ', '.join(nba[:3]) if nba else 'General business services'
            
            # Get web content if available
            web_content = company_data.get('_web_content', '')
            web_summary = company_data.get('_web_summary', '')
            web_keywords = company_data.get('_web_keywords', [])
            
            # Determine location
            location = 'India'
            if company_data.get('stj') and 'State - ' in str(company_data.get('stj')):
                try:
                    location = company_data['stj'].split('State - ')[1].split(',')[0]
                except:
                    pass
            
            # Compliance assessment
            returns_count = len(company_data.get('returns', []))
            compliance_status = self._assess_compliance_status(returns_count, company_data.get('sts'))
            
            # Registration info
            reg_date = company_data.get('rgdt', '')
            establishment_info = f"established {reg_date.split('/')[-1]}" if reg_date and '/' in reg_date else "an established entity"
            
            # Build enhanced prompt with web content
            prompt = f"""
            Create a professional business synopsis using both official GST data and web research:
            
            COMPANY OFFICIAL DATA:
            - Name: {company_name}
            - Activities: {business_activities}
            - Location: {location}
            - Establishment: {establishment_info}
            - GST Status: {compliance_status}
            - Returns Filed: {returns_count}
            
            WEB RESEARCH INSIGHTS:
            - Summary: {web_summary[:200] if web_summary else 'Limited web presence'}
            - Keywords: {', '.join(web_keywords[:5]) if web_keywords else 'Standard business'}
            
            ADDITIONAL WEB CONTENT:
            {web_content[:500] if web_content else 'No additional web information available'}
            
            Requirements:
            - Maximum 280 characters (Twitter-style)
            - Professional business directory tone
            - Combine GST data with web insights
            - Focus on actual business activities found online
            - Include location and key strength
            - If web content available, prioritize it over GST categories
            - No promotional language, factual only
            
            Format: Single professional paragraph describing what the company actually does.
            """
            
            response = await self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=120,
                temperature=0.2,  # Lower for more consistent output
                messages=[{"role": "user", "content": prompt}]
            )
            
            if hasattr(response, "content") and len(response.content) > 0:
                synopsis = response.content[0].text.strip()
                
                # Ensure character limit
                if len(synopsis) > 280:
                    synopsis = synopsis[:277] + "..."
                
                logger.info(f"AI synopsis with web content generated for {company_name}")
                return synopsis
            
        except Exception as e:
            logger.error(f"Enhanced AI synopsis generation failed for {company_data.get('lgnm', 'Unknown')}: {e}")
    
        # Fallback to rule-based synopsis
        return await self._generate_fallback_synopsis(company_data)
    
    def _assess_compliance_status(self, returns_count: int, status: str) -> str:
        """Assess compliance status based on returns and registration status"""
        if status != 'Active':
            return "inactive registration"
        
        if returns_count >= 20:
            return "strong compliance record"
        elif returns_count >= 10:
            return "good compliance history"
        elif returns_count >= 5:
            return "active GST filer"
        else:
            return "limited filing history"
    
    async def _generate_fallback_synopsis(self, company_data: Dict) -> str:
        """
        Generate synopsis without AI using rule-based approach
        Ensures consistent output even when AI is unavailable
        """
        company_name = company_data.get("lgnm", "Unknown Company")
        nba = company_data.get('nba', [])
        
        # Determine location
        location = 'India'
        if company_data.get('stj') and 'State - ' in str(company_data.get('stj')):
            try:
                location = company_data['stj'].split('State - ')[1].split(',')[0]
            except:
                pass
        
        # Build synopsis based on available data
        if nba and len(nba) > 0:
            primary_activity = nba[0].lower()
            
            # Template-based generation
            if 'manufacturing' in primary_activity:
                synopsis = f"{company_name} is a manufacturing company based in {location}, specializing in {primary_activity}."
            elif 'service' in primary_activity or 'consulting' in primary_activity:
                synopsis = f"{company_name} provides {primary_activity} based in {location}."
            elif 'trading' in primary_activity or 'wholesale' in primary_activity:
                synopsis = f"{company_name} is a {primary_activity} business operating from {location}."
            else:
                synopsis = f"{company_name} is engaged in {primary_activity}, based in {location}."
        else:
            synopsis = f"{company_name} is a business entity based in {location}, engaged in commercial activities."
        
        # Add compliance information if significant
        returns_count = len(company_data.get('returns', []))
        if returns_count > 15:
            synopsis += f" The company maintains active GST compliance with {returns_count} returns filed."
        elif returns_count > 8:
            synopsis += f" Maintains regular GST filings with {returns_count} returns on record."
        
        # Add establishment year if available
        if company_data.get('rgdt'):
            try:
                year = company_data['rgdt'].split('/')[-1]
                if len(year) == 4 and year.isdigit():
                    synopsis += f" Established in {year}."
            except:
                pass
        
        # Ensure character limit
        if len(synopsis) > 250:
            synopsis = synopsis[:247] + "..."
        
        return synopsis


# Backward compatibility class
class EnhancedAnthropicSynopsis:
    """Backward compatibility wrapper"""
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        self.analyzer = CompanyAnalyzer(anthropic_api_key)
    
    async def get_enhanced_synopsis(self, company_data: dict) -> str:
        """Legacy method for backward compatibility"""
        synopsis = await self.analyzer.get_anthropic_synopsis(company_data)
        return synopsis or "Company information not available"


# Convenience functions for backward compatibility
async def get_anthropic_synopsis(company_data: Dict, anthropic_api_key: Optional[str] = None) -> Optional[str]:
    """
    Convenience function for generating AI synopsis
    Maintains backward compatibility with existing code
    """
    analyzer = CompanyAnalyzer(anthropic_api_key)
    return await analyzer.get_anthropic_synopsis(company_data)


async def get_company_info_from_web(company_name: str, gstin: str = None, location: str = None) -> Dict[str, Union[str, List[str]]]:
    """
    Convenience function for web scraping
    Maintains backward compatibility with existing code
    """
    analyzer = CompanyAnalyzer()
    return await analyzer.get_company_info_from_web(company_name, gstin, location)


# Export main classes and functions
__all__ = [
    'CompanyAnalyzer',
    'EnhancedAnthropicSynopsis',
    'get_anthropic_synopsis',
    'get_company_info_from_web'
]


if __name__ == "__main__":
    # Simple test/demo
    async def test():
        analyzer = CompanyAnalyzer()
        
        # Test data
        test_company_data = {
            'lgnm': 'Test Company Private Limited',
            'nba': ['Software Development', 'IT Services'],
            'stj': 'State - Karnataka, Zone - Bangalore',
            'rgdt': '15/03/2020',
            'sts': 'Active',
            'returns': [{'rtntype': 'GSTR1'} for _ in range(12)]
        }
        
        print("Testing AI synopsis generation...")
        synopsis = await analyzer.get_anthropic_synopsis(test_company_data)
        print(f"Generated synopsis: {synopsis}")
        
        print("\nTesting web search...")
        web_info = await analyzer.get_company_info_from_web("Microsoft India", location="Karnataka")
        print(f"Found {len(web_info['sources'])} sources")
        print(f"Summary: {web_info['summary'][:100]}...")
    
    # Run test if script is executed directly
    asyncio.run(test())