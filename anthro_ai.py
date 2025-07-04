#!/usr/bin/env python3
"""
Enhanced AI Synopsis Generation with Web Scraping Intelligence
Provides comprehensive business analysis using Anthropic Claude AI
"""

import asyncio
import logging
import re
import json
from typing import Dict, Optional, List
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import anthropic
import os

# Configure logging
logger = logging.getLogger(__name__)

class WebIntelligenceGatherer:
    """Advanced web intelligence gathering for business insights."""
    
    def __init__(self):
        self.session = None
        self.timeout = 30
        self.max_retries = 3
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            },
            follow_redirects=True
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()
    
    async def search_company_info(self, company_name: str, gstin: str) -> Dict:
        """Search for comprehensive company information."""
        try:
            intelligence = {
                'company_name': company_name,
                'gstin': gstin,
                'web_presence': {},
                'business_info': {},
                'financial_indicators': {},
                'market_presence': {},
                'risk_factors': [],
                'sources': []
            }
            
            # Search patterns for different types of information
            search_queries = [
                f'"{company_name}" GSTIN {gstin}',
                f'"{company_name}" India business profile',
                f'"{company_name}" company information revenue',
                f'"{company_name}" contact details address',
                f'"{company_name}" business news updates'
            ]
            
            for query in search_queries[:2]:  # Limit searches to avoid rate limiting
                try:
                    search_results = await self._search_google(query)
                    if search_results:
                        intelligence['sources'].extend(search_results[:3])
                        
                        # Extract information from search results
                        for result in search_results[:2]:
                            content = await self._fetch_page_content(result.get('url', ''))
                            if content:
                                extracted_info = self._extract_business_info(content, company_name)
                                if extracted_info:
                                    intelligence['business_info'].update(extracted_info)
                                    
                    await asyncio.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Search query failed for '{query}': {e}")
                    continue
            
            # Enrich with company directory searches
            directory_info = await self._search_business_directories(company_name, gstin)
            if directory_info:
                intelligence['business_info'].update(directory_info)
            
            # Analyze web presence
            web_presence = await self._analyze_web_presence(company_name)
            intelligence['web_presence'] = web_presence
            
            return intelligence
            
        except Exception as e:
            logger.error(f"Error gathering company intelligence: {e}")
            return {
                'company_name': company_name,
                'gstin': gstin,
                'error': str(e),
                'sources': []
            }
    
    async def _search_google(self, query: str) -> List[Dict]:
        """Search Google for company information."""
        try:
            # Use DuckDuckGo instead of Google to avoid rate limiting
            search_url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
            
            response = await self.session.get(search_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                # Parse DuckDuckGo results
                for result in soup.find_all('a', class_='result__a')[:5]:
                    title = result.get_text(strip=True)
                    url = result.get('href', '')
                    
                    if url and title:
                        results.append({
                            'title': title,
                            'url': url,
                            'source': 'duckduckgo'
                        })
                
                return results
                
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []
    
    async def _fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch and clean page content."""
        try:
            if not url or not url.startswith(('http://', 'https://')):
                return None
                
            response = await self.session.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                    element.decompose()
                
                # Extract text content
                text = soup.get_text(strip=True)
                
                # Clean and limit text
                text = ' '.join(text.split())[:3000]  # Limit to 3000 chars
                return text
                
        except Exception as e:
            logger.debug(f"Failed to fetch content from {url}: {e}")
            return None
    
    def _extract_business_info(self, content: str, company_name: str) -> Dict:
        """Extract structured business information from content."""
        info = {}
        
        try:
            # Extract email addresses
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
            if emails:
                info['emails'] = list(set(emails[:3]))
            
            # Extract phone numbers (Indian format)
            phones = re.findall(r'(\+91[\s-]?)?[6-9]\d{2}[\s-]?\d{3}[\s-]?\d{4}', content)
            if phones:
                info['phones'] = list(set(phones[:3]))
            
            # Extract addresses (basic pattern)
            address_patterns = [
                r'(?i)address[:\s]*([^.\n]+(?:india|delhi|mumbai|bangalore|hyderabad|chennai|kolkata|pune)[^.\n]*)',
                r'(?i)([^.\n]*(?:road|street|avenue|building|complex|tower)[^.\n]*(?:india|delhi|mumbai|bangalore)[^.\n]*)'
            ]
            
            for pattern in address_patterns:
                addresses = re.findall(pattern, content)
                if addresses:
                    info['addresses'] = [addr.strip() for addr in addresses[:2]]
                    break
            
            # Extract business type/industry keywords
            industry_keywords = [
                'manufacturing', 'trading', 'services', 'software', 'technology',
                'pharmaceuticals', 'textiles', 'automotive', 'healthcare', 'education',
                'retail', 'wholesale', 'import', 'export', 'logistics'
            ]
            
            found_industries = []
            for keyword in industry_keywords:
                if keyword.lower() in content.lower():
                    found_industries.append(keyword.title())
            
            if found_industries:
                info['industries'] = found_industries[:3]
            
            # Extract revenue/financial indicators (basic patterns)
            financial_patterns = [
                r'(?i)revenue[:\s]*(?:rs\.?|₹|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:crore|lakh|million)?',
                r'(?i)turnover[:\s]*(?:rs\.?|₹|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:crore|lakh|million)?'
            ]
            
            for pattern in financial_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    info['financial_mentions'] = matches[:2]
                    break
            
        except Exception as e:
            logger.debug(f"Error extracting business info: {e}")
        
        return info
    
    async def _search_business_directories(self, company_name: str, gstin: str) -> Dict:
        """Search business directories for company information."""
        directories = [
            'zauba.com',
            'tofler.in',
            'businesslistingindia.in'
        ]
        
        info = {}
        
        for directory in directories[:1]:  # Limit to avoid rate limiting
            try:
                search_url = f"https://{directory}/search?q={company_name.replace(' ', '+')}"
                response = await self.session.get(search_url)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract directory-specific information
                    if 'zauba' in directory:
                        info.update(self._extract_zauba_info(soup, gstin))
                    elif 'tofler' in directory:
                        info.update(self._extract_tofler_info(soup, gstin))
                
                await asyncio.sleep(2)  # Rate limiting
                
            except Exception as e:
                logger.debug(f"Directory search failed for {directory}: {e}")
                continue
        
        return info
    
    def _extract_zauba_info(self, soup: BeautifulSoup, gstin: str) -> Dict:
        """Extract information from Zauba Corp."""
        info = {}
        
        try:
            # Look for company entries matching GSTIN
            company_links = soup.find_all('a', href=True)
            for link in company_links:
                if gstin.lower() in link.get('href', '').lower():
                    info['zauba_profile'] = link.get('href')
                    break
            
            # Extract visible company information
            company_rows = soup.find_all('tr')
            for row in company_rows[:10]:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    if any(keyword in key for keyword in ['company', 'business', 'activity']):
                        info[f'directory_{key}'] = value
        
        except Exception as e:
            logger.debug(f"Error extracting Zauba info: {e}")
        
        return info
    
    def _extract_tofler_info(self, soup: BeautifulSoup, gstin: str) -> Dict:
        """Extract information from Tofler."""
        info = {}
        
        try:
            # Look for company cards or listings
            company_cards = soup.find_all(['div', 'article'], class_=re.compile(r'company|listing|card'))
            
            for card in company_cards[:3]:
                text = card.get_text(strip=True)
                if gstin in text:
                    # Extract structured data from the card
                    lines = text.split('\n')
                    for line in lines[:5]:
                        if any(keyword in line.lower() for keyword in ['cin', 'industry', 'status']):
                            info[f'tofler_{line.split(":")[0].strip().lower()}'] = line.split(":", 1)[-1].strip()
        
        except Exception as e:
            logger.debug(f"Error extracting Tofler info: {e}")
        
        return info
    
    async def _analyze_web_presence(self, company_name: str) -> Dict:
        """Analyze company's web presence."""
        presence = {
            'has_website': False,
            'social_media': [],
            'digital_footprint': 'low'
        }
        
        try:
            # Check for common website patterns
            domain_patterns = [
                company_name.lower().replace(' ', ''),
                company_name.lower().replace(' ', '-'),
                ''.join([word[0] for word in company_name.split()]).lower()
            ]
            
            for pattern in domain_patterns[:2]:
                try:
                    website_url = f"https://{pattern}.com"
                    response = await self.session.head(website_url, timeout=10)
                    if response.status_code == 200:
                        presence['has_website'] = True
                        presence['website_url'] = website_url
                        break
                except:
                    continue
            
            # Check social media presence (basic)
            social_platforms = ['linkedin', 'facebook', 'twitter']
            for platform in social_platforms:
                try:
                    social_url = f"https://{platform}.com/search/top?q={company_name.replace(' ', '%20')}"
                    response = await self.session.head(social_url, timeout=5)
                    if response.status_code == 200:
                        presence['social_media'].append(platform)
                except:
                    continue
            
            # Determine digital footprint
            score = 0
            if presence['has_website']:
                score += 3
            score += len(presence['social_media'])
            
            if score >= 4:
                presence['digital_footprint'] = 'high'
            elif score >= 2:
                presence['digital_footprint'] = 'medium'
            else:
                presence['digital_footprint'] = 'low'
        
        except Exception as e:
            logger.debug(f"Error analyzing web presence: {e}")
        
        return presence

class EnhancedBusinessAnalyzer:
    """Advanced business analysis using AI and web intelligence."""
    
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-haiku-20240307"  # Using Haiku for faster responses
    
    async def generate_comprehensive_synopsis(self, company_data: Dict, compliance_score: float, web_intelligence: Dict = None) -> str:
        """Generate comprehensive business synopsis using AI and web intelligence."""
        try:
            # Prepare comprehensive context
            context = self._prepare_analysis_context(company_data, compliance_score, web_intelligence)
            
            # Create detailed prompt
            prompt = self._create_analysis_prompt(context)
            
            # Get AI analysis
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            synopsis = response.content[0].text.strip()
            
            # Enhance with web intelligence insights
            if web_intelligence and web_intelligence.get('business_info'):
                synopsis = self._enhance_with_web_intelligence(synopsis, web_intelligence)
            
            return synopsis
            
        except Exception as e:
            logger.error(f"AI synopsis generation failed: {e}")
            return self._generate_fallback_synopsis(company_data, compliance_score, web_intelligence)
    
    def _prepare_analysis_context(self, company_data: Dict, compliance_score: float, web_intelligence: Dict = None) -> Dict:
        """Prepare comprehensive context for AI analysis."""
        context = {
            'basic_info': {
                'company_name': company_data.get('lgnm', 'Unknown'),
                'gstin': company_data.get('gstin', 'N/A'),
                'status': company_data.get('sts', 'Unknown'),
                'state': company_data.get('stj', 'Unknown'),
                'business_type': company_data.get('ctb', 'Unknown'),
                'registration_date': company_data.get('rgdt', 'Unknown')
            },
            'compliance': {
                'score': compliance_score,
                'grade': self._get_compliance_grade(compliance_score),
                'returns_filed': len(company_data.get('returns', [])),
                'gstr1_count': len([r for r in company_data.get('returns', []) if r.get('rtntype') == 'GSTR1']),
                'gstr3b_count': len([r for r in company_data.get('returns', []) if r.get('rtntype') == 'GSTR3B'])
            },
            'filing_analysis': company_data.get('_late_filing_analysis', {}),
            'web_intelligence': web_intelligence or {}
        }
        
        return context
    
    def _create_analysis_prompt(self, context: Dict) -> str:
        """Create comprehensive analysis prompt for AI."""
        basic_info = context['basic_info']
        compliance = context['compliance']
        filing_analysis = context['filing_analysis']
        web_intel = context['web_intelligence']
        
        prompt = f"""
Analyze this Indian GST-registered business and provide a comprehensive, professional synopsis:

COMPANY INFORMATION:
- Name: {basic_info['company_name']}
- GSTIN: {basic_info['gstin']}
- Status: {basic_info['status']}
- Business Type: {basic_info['business_type']}
- State: {basic_info['state']}
- Registration Date: {basic_info['registration_date']}

COMPLIANCE PROFILE:
- Overall Score: {compliance['score']}/100 ({compliance['grade']} grade)
- Total Returns Filed: {compliance['returns_filed']}
- GSTR-1 Returns: {compliance['gstr1_count']}
- GSTR-3B Returns: {compliance['gstr3b_count']}

FILING BEHAVIOR:
- Late Returns: {filing_analysis.get('late_count', 0)}
- On-time Returns: {filing_analysis.get('on_time_count', 0)}
- Average Delay: {filing_analysis.get('average_delay', 0):.1f} days
"""

        if web_intel.get('business_info'):
            business_info = web_intel['business_info']
            prompt += f"""
WEB INTELLIGENCE:
- Digital Presence: {web_intel.get('web_presence', {}).get('digital_footprint', 'unknown')}
- Industries: {', '.join(business_info.get('industries', ['Not specified']))}
- Contact Points: {len(business_info.get('emails', []))} emails, {len(business_info.get('phones', []))} phones
- Financial Mentions: {business_info.get('financial_mentions', ['None found'])}
"""

        prompt += """
Provide a 150-200 word professional business synopsis covering:
1. Business overview and operational status
2. Compliance performance assessment
3. Risk factors and strengths
4. Market positioning insights (if available)
5. Overall business health summary

Focus on practical insights for business decision-making. Be specific, factual, and professional.
"""
        
        return prompt
    
    def _enhance_with_web_intelligence(self, synopsis: str, web_intelligence: Dict) -> str:
        """Enhance synopsis with web intelligence insights."""
        try:
            business_info = web_intelligence.get('business_info', {})
            web_presence = web_intelligence.get('web_presence', {})
            
            enhancements = []
            
            # Add digital presence insights
            if web_presence.get('has_website'):
                enhancements.append("The company maintains an active web presence")
            elif web_presence.get('digital_footprint') == 'low':
                enhancements.append("Limited digital presence observed")
            
            # Add contact/operational insights
            if business_info.get('emails') or business_info.get('phones'):
                enhancements.append("Accessible contact information available")
            
            # Add industry insights
            if business_info.get('industries'):
                industries = ', '.join(business_info['industries'][:2])
                enhancements.append(f"Active in {industries} sectors")
            
            if enhancements:
                synopsis += f" {'. '.join(enhancements)}."
            
            return synopsis
            
        except Exception as e:
            logger.debug(f"Error enhancing synopsis: {e}")
            return synopsis
    
    def _get_compliance_grade(self, score: float) -> str:
        """Get compliance grade from score."""
        if score >= 90:
            return "A+ (Excellent)"
        elif score >= 80:
            return "A (Very Good)"
        elif score >= 70:
            return "B (Good)"
        elif score >= 60:
            return "C (Average)"
        else:
            return "D (Needs Improvement)"
    
    def _generate_fallback_synopsis(self, company_data: Dict, compliance_score: float, web_intelligence: Dict = None) -> str:
        """Generate fallback synopsis when AI is unavailable."""
        company_name = company_data.get('lgnm', 'Company')
        status = company_data.get('sts', 'Unknown')
        returns_count = len(company_data.get('returns', []))
        
        grade = self._get_compliance_grade(compliance_score)
        
        synopsis = f"{company_name} is a GST-registered entity with {status.lower()} status. "
        synopsis += f"The company has filed {returns_count} returns and maintains a compliance score of {compliance_score:.0f}/100 ({grade}). "
        
        if compliance_score >= 80:
            synopsis += "The business demonstrates strong regulatory compliance with consistent filing patterns. "
        elif compliance_score >= 60:
            synopsis += "The business shows moderate compliance with room for improvement in filing consistency. "
        else:
            synopsis += "The business requires attention to improve its compliance standing and filing regularity. "
        
        # Add web intelligence if available
        if web_intelligence and web_intelligence.get('business_info'):
            business_info = web_intelligence['business_info']
            if business_info.get('industries'):
                industries = ', '.join(business_info['industries'][:2])
                synopsis += f"The company operates in {industries} sector(s). "
        
        synopsis += "This analysis is based on available GST filing data and public information."
        
        return synopsis

# Main function for external usage
async def get_anthropic_synopsis(company_data: Dict, compliance_score: float = None) -> Optional[str]:
    """
    Main function to get comprehensive business synopsis.
    
    Args:
        company_data: GST company data from API
        compliance_score: Calculated compliance score
    
    Returns:
        Comprehensive business synopsis or None if failed
    """
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.warning("Anthropic API key not configured")
            return None
        
        company_name = company_data.get('lgnm', '')
        gstin = company_data.get('gstin', '')
        
        if not company_name:
            logger.warning("Company name not available for synopsis")
            return None
        
        # Initialize analyzer
        analyzer = EnhancedBusinessAnalyzer(api_key)
        
        # Gather web intelligence
        web_intelligence = {}
        try:
            async with WebIntelligenceGatherer() as gatherer:
                web_intelligence = await gatherer.search_company_info(company_name, gstin)
                logger.info(f"Web intelligence gathered for {company_name}")
        except Exception as e:
            logger.warning(f"Web intelligence gathering failed: {e}")
        
        # Generate comprehensive synopsis
        synopsis = await analyzer.generate_comprehensive_synopsis(
            company_data, 
            compliance_score or 0, 
            web_intelligence
        )
        
        logger.info(f"Synopsis generated successfully for {company_name}")
        return synopsis
        
    except Exception as e:
        logger.error(f"Synopsis generation failed: {e}")
        return None

# Alternative simpler function for basic synopsis
def get_basic_synopsis(company_data: Dict, compliance_score: float) -> str:
    """Generate basic synopsis without AI or web scraping."""
    analyzer = EnhancedBusinessAnalyzer("")  # Empty API key for fallback
    return analyzer._generate_fallback_synopsis(company_data, compliance_score)

if __name__ == "__main__":
    # Test function
    async def test_synopsis():
        test_data = {
            'lgnm': 'Test Company Private Limited',
            'gstin': '07AABCU9603R1ZX',
            'sts': 'Active',
            'stj': 'State - Delhi, Zone - Delhi',
            'ctb': 'Private Limited Company',
            'rgdt': '01/04/2019',
            'returns': [
                {'rtntype': 'GSTR1', 'dof': '10/05/2023'},
                {'rtntype': 'GSTR3B', 'dof': '20/05/2023'}
            ]
        }
        
        synopsis = await get_anthropic_synopsis(test_data, 85.0)
        print("Generated Synopsis:")
        print(synopsis)
    
    asyncio.run(test_synopsis())