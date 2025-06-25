#!/usr/bin/env python3
"""
Enhanced GST Company Analysis Module with AI Integration
Optimized AI-powered company analysis and web scraping for loan assessments
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
    logger.warning("Google search not available - falling back to direct search only")
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
    Enhanced company analysis class with AI and web scraping capabilities
    Optimized for loan assessment and business intelligence
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
        Returns list of relevant URLs for loan assessment
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
        
        urls = []
        
        try:
            # Construct search queries optimized for business information
            search_queries = [
                f'"{company_name}" company business profile',
                f'"{company_name}" financial information revenue',
                f'"{company_name}" company overview about'
            ]
            
            if location:
                search_queries.append(f'"{company_name}" {location} business')
            
            # Use Google search if available
            if HAS_GOOGLE_SEARCH:
                for query in search_queries[:2]:  # Limit to 2 queries to avoid rate limits
                    try:
                        search_results = google_search(query, num_results=3, sleep_interval=1)
                        for url in search_results:
                            if self._is_relevant_url(url):
                                urls.append(url)
                        
                        if len(urls) >= 5:  # Limit total URLs
                            break
                            
                    except Exception as e:
                        logger.warning(f"Google search failed for query '{query}': {e}")
                        continue
            
            # Fallback to direct searches for known business websites
            if not urls:
                urls = await self._search_direct_sources(company_name, location)
            
            # Cache results
            self._cache[cache_key] = urls
            
            logger.info(f"Found {len(urls)} relevant URLs for {company_name}")
            return urls[:10]  # Limit to top 10 URLs
            
        except Exception as e:
            logger.error(f"Web search failed for {company_name}: {e}")
            return []
    
    def _is_relevant_url(self, url: str) -> bool:
        """Check if URL is relevant for business analysis"""
        # Filter out irrelevant sources
        irrelevant_domains = [
            'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com',
            'pinterest.com', 'tiktok.com', 'reddit.com', 'quora.com',
            'amazon.com', 'flipkart.com', 'ebay.com'
        ]
        
        # Prefer business-relevant sources
        relevant_domains = [
            'linkedin.com', 'crunchbase.com', 'bloomberg.com', 'reuters.com',
            'business-standard.com', 'economictimes.com', 'livemint.com',
            'moneycontrol.com', 'zauba.com', 'mca.gov.in', 'companieshouse.gov.uk'
        ]
        
        url_lower = url.lower()
        
        # Exclude irrelevant domains
        if any(domain in url_lower for domain in irrelevant_domains):
            return False
        
        # Prefer relevant domains
        if any(domain in url_lower for domain in relevant_domains):
            return True
        
        # Include company websites and business directories
        if any(keyword in url_lower for keyword in ['about', 'company', 'business', 'profile', 'overview']):
            return True
        
        return True  # Default to include if not explicitly filtered out
    
    async def _search_direct_sources(self, company_name: str, location: str = None) -> List[str]:
        """Search direct business information sources"""
        urls = []
        
        # Construct potential company website URLs
        company_slug = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
        potential_domains = [
            f"https://{company_slug}.com",
            f"https://www.{company_slug}.com",
            f"https://{company_slug}.co.in",
            f"https://www.{company_slug}.co.in"
        ]
        
        for domain in potential_domains:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.head(domain)
                    if response.status_code == 200:
                        urls.append(domain)
                        break  # Found working domain
            except:
                continue
        
        # Add known business directory searches
        business_directories = [
            f"https://www.justdial.com/search/?q={company_name.replace(' ', '%20')}",
            f"https://www.indiamart.com/search.mp?ss={company_name.replace(' ', '%20')}",
        ]
        
        urls.extend(business_directories[:2])  # Limit to 2 directories
        
        return urls
    
    async def scrape_company_info(self, urls: List[str]) -> Dict[str, Union[str, List[str]]]:
        """
        Scrape company information from URLs with enhanced extraction for loan assessment
        """
        if not HAS_BEAUTIFULSOUP:
            return {"web_content": "", "summary": "", "keywords": [], "sources": []}
        
        all_content = []
        keywords = set()
        successful_sources = []
        
        for url in urls:
            try:
                async with httpx.AsyncClient(
                    timeout=self.http_timeout,
                    headers={"User-Agent": self.user_agent},
                    follow_redirects=True
                ) as client:
                    
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Remove unwanted elements
                        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                            element.decompose()
                        
                        # Extract business-relevant content
                        content = self._extract_business_content(soup)
                        
                        if content:
                            all_content.append(content)
                            successful_sources.append(url)
                            
                            # Extract keywords for business analysis
                            page_keywords = self._extract_business_keywords(content)
                            keywords.update(page_keywords)
                            
                            logger.info(f"Successfully scraped content from {url}")
                        
                        # Limit processing time per URL
                        await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")
                continue
        
        # Combine and clean content
        combined_content = ' '.join(all_content)
        cleaned_content = self._clean_text(combined_content)
        
        # Generate summary
        summary = self._generate_summary(cleaned_content)
        
        return {
            "web_content": cleaned_content[:2000],  # Limit content size
            "summary": summary,
            "keywords": list(keywords)[:20],  # Top 20 keywords
            "sources": successful_sources
        }
    
    def _extract_business_content(self, soup: BeautifulSoup) -> str:
        """Extract business-relevant content from webpage"""
        content_selectors = [
            'section[class*="about"]',
            'div[class*="about"]',
            'section[class*="company"]',
            'div[class*="company"]',
            'section[class*="business"]',
            'div[class*="overview"]',
            '.company-description',
            '.about-company',
            '.business-overview',
            'main',
            'article'
        ]
        
        extracted_content = []
        
        # Try specific selectors first
        for selector in content_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if len(text) > 50:  # Only include substantial content
                    extracted_content.append(text)
        
        # Fallback to general content extraction
        if not extracted_content:
            # Look for paragraphs with business-related content
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 50 and self._contains_business_keywords(text):
                    extracted_content.append(text)
        
        return ' '.join(extracted_content)
    
    def _contains_business_keywords(self, text: str) -> bool:
        """Check if text contains business-relevant keywords"""
        business_keywords = [
            'company', 'business', 'services', 'products', 'industry', 'founded',
            'established', 'revenue', 'turnover', 'employees', 'clients', 'customers',
            'manufacturing', 'trading', 'exports', 'imports', 'operations', 'technology'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in business_keywords)
    
    def _extract_business_keywords(self, content: str) -> set:
        """Extract business-relevant keywords from content"""
        # Business-specific keyword patterns
        business_patterns = [
            r'\b(?:manufacturing|trading|services|consulting|technology|software|hardware)\b',
            r'\b(?:revenue|turnover|profit|income|sales)\b',
            r'\b(?:employees|staff|team|workforce)\b',
            r'\b(?:clients|customers|partners|suppliers)\b',
            r'\b(?:founded|established|incorporated|started)\b',
            r'\b(?:industry|sector|market|business)\b'
        ]
        
        keywords = set()
        content_lower = content.lower()
        
        for pattern in business_patterns:
            matches = re.findall(pattern, content_lower)
            keywords.update(matches)
        
        # Extract company-specific terms
        company_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
        keywords.update([term.lower() for term in company_terms if len(term.split()) <= 3])
        
        return keywords
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?()-]', '', text)
        
        # Remove very short lines
        lines = text.split('\n')
        lines = [line.strip() for line in lines if len(line.strip()) > 10]
        
        return ' '.join(lines).strip()
    
    def _generate_summary(self, content: str) -> str:
        """Generate a brief summary of the scraped content"""
        if not content:
            return "No business information found"
        
        # Extract first few sentences that contain business information
        sentences = re.split(r'[.!?]+', content)
        business_sentences = []
        
        for sentence in sentences[:10]:  # Look at first 10 sentences
            if len(sentence.strip()) > 20 and self._contains_business_keywords(sentence):
                business_sentences.append(sentence.strip())
                if len(business_sentences) >= 3:  # Limit to 3 sentences
                    break
        
        if business_sentences:
            return '. '.join(business_sentences) + '.'
        else:
            # Fallback to first 200 characters
            return content[:200] + '...' if len(content) > 200 else content
    
    async def get_company_info_from_web(self, company_name: str, gstin: str = None, location: str = None) -> Dict[str, Union[str, List[str]]]:
        """
        Get comprehensive company information from web sources
        Optimized for loan assessment and business analysis
        """
        try:
            logger.info(f"Gathering web information for {company_name}")
            
            # Search for company URLs
            urls = await self.search_company_web(company_name, location)
            
            if not urls:
                logger.warning(f"No URLs found for {company_name}")
                return {
                    "web_content": "",
                    "summary": f"Limited information available for {company_name}",
                    "keywords": [],
                    "sources": []
                }
            
            # Scrape company information
            web_info = await self.scrape_company_info(urls)
            
            # Enhanced summary with loan-relevant information
            if web_info["web_content"]:
                enhanced_summary = self._create_enhanced_summary(
                    company_name, web_info["web_content"], web_info["keywords"]
                )
                web_info["summary"] = enhanced_summary
            
            logger.info(f"Successfully gathered web information for {company_name}")
            return web_info
            
        except Exception as e:
            logger.error(f"Failed to get web information for {company_name}: {e}")
            return {
                "web_content": "",
                "summary": f"Information gathering failed for {company_name}",
                "keywords": [],
                "sources": []
            }
    
    def _create_enhanced_summary(self, company_name: str, content: str, keywords: List[str]) -> str:
        """Create enhanced summary with loan-relevant insights"""
        # Extract business type and industry
        industry_keywords = [kw for kw in keywords if kw in [
            'manufacturing', 'trading', 'services', 'technology', 'consulting',
            'software', 'hardware', 'retail', 'wholesale', 'export', 'import'
        ]]
        
        summary_parts = [f"Business information for {company_name}:"]
        
        if industry_keywords:
            summary_parts.append(f"Industry: {', '.join(industry_keywords[:3])}")
        
        # Look for business size indicators
        if any(kw in keywords for kw in ['revenue', 'turnover', 'sales']):
            summary_parts.append("Financial information available in business records")
        
        if any(kw in keywords for kw in ['employees', 'staff', 'team']):
            summary_parts.append("Employment information indicates operational business")
        
        # Add content summary
        content_summary = self._generate_summary(content)
        if content_summary:
            summary_parts.append(content_summary)
        
        return '. '.join(summary_parts)
    
    async def get_anthropic_synopsis(self, company_data: Dict) -> Optional[str]:
        """
        Generate AI-powered company synopsis with enhanced loan assessment focus
        """
        if not self.anthropic_client:
            logger.warning("Anthropic client not available")
            return self._generate_fallback_synopsis(company_data)
        
        try:
            # Prepare data for AI analysis
            analysis_data = self._prepare_ai_analysis_data(company_data)
            
            # Enhanced prompt for loan assessment
            prompt = self._create_enhanced_ai_prompt(analysis_data)
            
            # Get AI analysis
            response = await self.anthropic_client.messages.create(
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
            
            synopsis = response.content[0].text.strip()
            
            # Validate and clean synopsis
            synopsis = self._validate_synopsis(synopsis)
            
            logger.info(f"Generated AI synopsis for {company_data.get('lgnm', 'Unknown')}")
            return synopsis
            
        except Exception as e:
            logger.error(f"AI synopsis generation failed: {e}")
            return self._generate_fallback_synopsis(company_data)
    
    def _prepare_ai_analysis_data(self, company_data: Dict) -> Dict:
        """Prepare company data for AI analysis with loan focus"""
        analysis_data = {
            "company_name": company_data.get("lgnm", "Unknown"),
            "registration_status": company_data.get("sts", "Unknown"),
            "business_type": company_data.get("ctb", "Unknown"),
            "registration_date": company_data.get("rgdt", "Unknown"),
            "state": "Unknown"
        }
        
        # Extract state information
        if company_data.get('stj') and 'State - ' in str(company_data.get('stj')):
            try:
                analysis_data["state"] = company_data['stj'].split('State - ')[1].split(',')[0]
            except:
                pass
        
        # Business activities
        business_activities = company_data.get("nba", [])
        if business_activities:
            analysis_data["business_activities"] = business_activities[:3]  # Top 3 activities
        
        # GST filing information
        returns = company_data.get("returns", [])
        if returns:
            analysis_data["total_returns"] = len(returns)
            analysis_data["gstr1_count"] = len([r for r in returns if r.get("rtntype") == "GSTR1"])
            analysis_data["gstr3b_count"] = len([r for r in returns if r.get("rtntype") == "GSTR3B"])
        
        # Late filing analysis
        late_filing_analysis = company_data.get('_late_filing_analysis', {})
        if late_filing_analysis:
            analysis_data["late_filings"] = late_filing_analysis.get('late_count', 0)
            analysis_data["on_time_filings"] = late_filing_analysis.get('on_time_count', 0)
        
        # Web information if available
        if company_data.get('_web_summary'):
            analysis_data["web_summary"] = company_data['_web_summary'][:500]  # Limit length
        
        return analysis_data
    
    def _create_enhanced_ai_prompt(self, analysis_data: Dict) -> str:
        """Create enhanced AI prompt focused on loan assessment"""
        prompt = f"""Analyze this Indian business for loan assessment purposes. Provide a concise professional summary (150-200 words) covering business viability, GST compliance, and loan suitability.

Company Details:
- Name: {analysis_data.get('company_name')}
- Status: {analysis_data.get('registration_status')}
- Type: {analysis_data.get('business_type')}
- State: {analysis_data.get('state')}
- Registration: {analysis_data.get('registration_date')}

GST Compliance:
- Total Returns: {analysis_data.get('total_returns', 0)}
- GSTR-1 Filed: {analysis_data.get('gstr1_count', 0)}
- GSTR-3B Filed: {analysis_data.get('gstr3b_count', 0)}
- Late Filings: {analysis_data.get('late_filings', 0)}
- On-time Filings: {analysis_data.get('on_time_filings', 0)}

Business Activities: {', '.join(analysis_data.get('business_activities', [])) if analysis_data.get('business_activities') else 'Not specified'}

{f"Additional Info: {analysis_data.get('web_summary')}" if analysis_data.get('web_summary') else ''}

Focus on:
1. Business legitimacy and operational status
2. GST compliance patterns and reliability
3. Industry type and business model viability
4. Overall loan creditworthiness indicators

Provide a professional assessment suitable for loan evaluation."""
        
        return prompt
    
    def _validate_synopsis(self, synopsis: str) -> str:
        """Validate and clean AI-generated synopsis"""
        if not synopsis:
            return "Company analysis not available"
        
        # Remove any potential harmful content
        synopsis = re.sub(r'[^\w\s.,!?()-]', '', synopsis)
        
        # Ensure reasonable length
        if len(synopsis) > 500:
            synopsis = synopsis[:497] + "..."
        elif len(synopsis) < 50:
            return "Brief company analysis available"
        
        return synopsis.strip()
    
    def _generate_fallback_synopsis(self, company_data: Dict) -> str:
        """Generate fallback synopsis when AI is not available"""
        company_name = company_data.get("lgnm", "Unknown Company")
        status = company_data.get("sts", "Unknown")
        returns = company_data.get("returns", [])
        
        synopsis_parts = [f"{company_name} is a GST-registered business"]
        
        if status == "Active":
            synopsis_parts.append("with active registration status")
        
        if returns:
            returns_count = len(returns)
            if returns_count > 8:
                synopsis_parts.append(f"demonstrating good compliance with {returns_count} GST returns filed")
            elif returns_count > 4:
                synopsis_parts.append(f"showing moderate compliance with {returns_count} GST returns")
            else:
                synopsis_parts.append(f"with limited filing history of {returns_count} returns")
        
        # Add business type if available
        business_type = company_data.get("ctb", "")
        if business_type and business_type != "Unknown":
            synopsis_parts.append(f"operating as {business_type}")
        
        # Add establishment info
        if company_data.get('rgdt'):
            try:
                year = company_data['rgdt'].split('/')[-1]
                if len(year) == 4 and year.isdigit():
                    synopsis_parts.append(f"established in {year}")
            except:
                pass
        
        synopsis = '. '.join(synopsis_parts) + '.'
        
        # Ensure character limit
        if len(synopsis) > 300:
            synopsis = synopsis[:297] + "..."
        
        return synopsis

# Backward compatibility functions
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