import os
import asyncio
import httpx
import logging
from typing import Dict, Optional
from bs4 import BeautifulSoup
import re
from urllib.parse import quote_plus
import anthropic

logger = logging.getLogger(__name__)

class CompanyIntelligence:
    def __init__(self, anthropic_api_key: str):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        
    async def get_company_synopsis(self, company_data: Dict, compliance_score: float) -> Optional[str]:
        """Generate comprehensive company synopsis using web data + AI analysis."""
        try:
            company_name = company_data.get("lgnm", "Unknown Company")
            gstin = company_data.get("gstin", "")
            
            # Step 1: Gather web intelligence
            web_data = await self.gather_web_intelligence(company_name, gstin)
            
            # Step 2: Combine all data for AI analysis
            context_data = {
                "gst_data": company_data,
                "compliance_score": compliance_score,
                "web_intelligence": web_data,
                "company_name": company_name,
                "gstin": gstin
            }
            
            # Step 3: Generate AI synopsis
            synopsis = await self.generate_ai_synopsis(context_data)
            
            return synopsis
            
        except Exception as e:
            logger.error(f"Error generating company synopsis: {e}")
            return self.generate_fallback_synopsis(company_data, compliance_score)
    
    async def gather_web_intelligence(self, company_name: str, gstin: str) -> Dict:
        """Gather intelligence from multiple web sources."""
        web_data = {
            "search_results": [],
            "company_website": None,
            "business_info": {},
            "social_presence": {},
            "news_mentions": [],
            "financial_insights": {}
        }
        
        try:
            # Search for company information
            search_queries = [
                f'"{company_name}" GSTIN {gstin}',
                f'"{company_name}" company profile business',
                f'"{company_name}" revenue turnover business overview',
                f'"{company_name}" products services industry'
            ]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for query in search_queries[:2]:  # Limit to 2 queries for performance
                    try:
                        search_data = await self.search_web(client, query)
                        web_data["search_results"].extend(search_data)
                        await asyncio.sleep(1)  # Rate limiting
                    except Exception as e:
                        logger.warning(f"Search failed for query '{query}': {e}")
                        continue
            
            # Extract insights from search results
            web_data["business_info"] = self.extract_business_insights(web_data["search_results"], company_name)
            
        except Exception as e:
            logger.error(f"Web intelligence gathering failed: {e}")
        
        return web_data
    
    async def search_web(self, client: httpx.AsyncClient, query: str) -> list:
        """Search the web for company information."""
        results = []
        
        try:
            # Use DuckDuckGo search (no API key required)
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = await client.get(search_url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract search results
            for result in soup.find_all('div', class_='result')[:5]:  # Top 5 results
                try:
                    title_elem = result.find('a', class_='result__a')
                    snippet_elem = result.find('a', class_='result__snippet')
                    
                    if title_elem and snippet_elem:
                        title = title_elem.get_text(strip=True)
                        snippet = snippet_elem.get_text(strip=True)
                        link = title_elem.get('href', '')
                        
                        results.append({
                            'title': title,
                            'snippet': snippet,
                            'link': link,
                            'source': 'web_search'
                        })
                        
                except Exception as e:
                    logger.warning(f"Error parsing search result: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            
        return results
    
    def extract_business_insights(self, search_results: list, company_name: str) -> Dict:
        """Extract business insights from search results."""
        insights = {
            "industry": [],
            "products_services": [],
            "business_type": [],
            "key_activities": [],
            "market_presence": [],
            "financial_indicators": []
        }
        
        # Keywords for different categories
        industry_keywords = ['manufacturing', 'trading', 'services', 'technology', 'software', 'retail', 'wholesale', 'construction', 'pharmaceuticals', 'textiles', 'automotive', 'food', 'chemicals', 'electronics']
        business_keywords = ['private limited', 'limited company', 'partnership', 'proprietorship', 'corporation', 'enterprise', 'industries', 'group', 'holdings']
        financial_keywords = ['revenue', 'turnover', 'crores', 'lakhs', 'profit', 'growth', 'expansion', 'investment']
        
        for result in search_results:
            text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
            
            # Extract industry information
            for keyword in industry_keywords:
                if keyword in text and keyword not in insights["industry"]:
                    insights["industry"].append(keyword.title())
            
            # Extract business type
            for keyword in business_keywords:
                if keyword in text and keyword not in insights["business_type"]:
                    insights["business_type"].append(keyword.title())
            
            # Extract financial indicators
            for keyword in financial_keywords:
                if keyword in text:
                    # Extract surrounding context
                    sentences = text.split('.')
                    for sentence in sentences:
                        if keyword in sentence and len(sentence) < 200:
                            insights["financial_indicators"].append(sentence.strip())
                            break
            
            # Extract key activities (look for action words)
            activity_patterns = [
                r'manufactures?\s+([^.,]+)',
                r'produces?\s+([^.,]+)',
                r'provides?\s+([^.,]+)',
                r'specializes?\s+in\s+([^.,]+)',
                r'engaged\s+in\s+([^.,]+)'
            ]
            
            for pattern in activity_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches[:2]:  # Limit matches
                    clean_match = re.sub(r'[^\w\s]', '', match).strip()
                    if len(clean_match) > 5 and len(clean_match) < 100:
                        insights["key_activities"].append(clean_match.title())
        
        # Remove duplicates and limit results
        for key in insights:
            insights[key] = list(set(insights[key]))[:3]  # Max 3 items per category
        
        return insights
    
    async def generate_ai_synopsis(self, context_data: Dict) -> str:
        """Generate AI synopsis using Anthropic Claude."""
        try:
            company_name = context_data["company_name"]
            gstin = context_data["gstin"]
            gst_data = context_data["gst_data"]
            compliance_score = context_data["compliance_score"]
            web_data = context_data["web_intelligence"]
            business_info = web_data.get("business_info", {})
            
            # Build comprehensive prompt
            prompt = f"""
            As a business intelligence analyst, create a comprehensive company overview for {company_name} (GSTIN: {gstin}).

            GST Registration Data:
            - Status: {gst_data.get('sts', 'Unknown')}
            - Registration Date: {gst_data.get('rgdt', 'Unknown')}
            - Business Type: {gst_data.get('ctb', 'Unknown')}
            - State: {gst_data.get('stj', 'Unknown')}
            - Nature of Business: {', '.join(gst_data.get('nba', [])[:3]) if gst_data.get('nba') else 'Unknown'}
            - Returns Filed: {len(gst_data.get('returns', []))} total returns
            - Compliance Score: {compliance_score}%

            Web Intelligence Gathered:
            - Industry Categories: {', '.join(business_info.get('industry', [])) if business_info.get('industry') else 'Not identified'}
            - Business Type Indicators: {', '.join(business_info.get('business_type', [])) if business_info.get('business_type') else 'Not identified'}
            - Key Activities: {', '.join(business_info.get('key_activities', [])) if business_info.get('key_activities') else 'Not identified'}
            - Financial Indicators: {'; '.join(business_info.get('financial_indicators', [])[:2]) if business_info.get('financial_indicators') else 'No financial data found'}

            Search Results Summary:
            {self._format_search_results(web_data.get('search_results', []))}

            Create a 3-4 sentence business overview that:
            1. Describes what the company does based on ALL available data
            2. Mentions their industry/sector and key business activities
            3. References their market presence or scale if evident
            4. Includes a brief compliance assessment
            5. Avoids generic statements and focuses on specific insights

            Write in a professional, analytical tone suitable for business intelligence reports.
            """
            
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=300,
                temperature=0.3,
                messages=[{
                    "role": "user", 
                    "content": prompt
                }]
            )
            
            synopsis = response.content[0].text.strip()
            
            # Ensure minimum quality
            if len(synopsis) < 100 or "compliance score" in synopsis.lower() and len(synopsis) < 150:
                return self.generate_fallback_synopsis(gst_data, compliance_score)
            
            return synopsis
            
        except Exception as e:
            logger.error(f"AI synopsis generation failed: {e}")
            return self.generate_fallback_synopsis(context_data["gst_data"], context_data["compliance_score"])
    
    def _format_search_results(self, search_results: list) -> str:
        """Format search results for the AI prompt."""
        if not search_results:
            return "No web search results available."
        
        formatted = []
        for i, result in enumerate(search_results[:3], 1):
            title = result.get('title', 'No title')[:100]
            snippet = result.get('snippet', 'No description')[:200]
            formatted.append(f"{i}. {title}: {snippet}")
        
        return '\n'.join(formatted)
    
    def generate_fallback_synopsis(self, company_data: Dict, compliance_score: float) -> str:
        """Generate a basic synopsis when AI/web scraping fails."""
        company_name = company_data.get("lgnm", "This company")
        business_type = company_data.get("ctb", "business entity")
        state = company_data.get("stj", "").split("State - ")[-1].split(",")[0] if company_data.get("stj") else "India"
        
        activities = company_data.get("nba", [])
        activity_text = f"engaged in {', '.join(activities[:2])}" if activities else "operating in its registered business activities"
        
        compliance_text = "excellent" if compliance_score >= 90 else "good" if compliance_score >= 75 else "moderate" if compliance_score >= 60 else "developing"
        
        return f"{company_name} is a {business_type.lower()} based in {state}, {activity_text}. The company maintains {compliance_text} GST compliance standards with a score of {compliance_score}%, having filed {len(company_data.get('returns', []))} returns to date. This indicates {'strong regulatory adherence and operational stability' if compliance_score >= 75 else 'room for improvement in compliance management'}."

# Main function for backward compatibility
async def get_anthropic_synopsis(company_data: Dict, compliance_score: float) -> Optional[str]:
    """Main function to get company synopsis."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not found")
        return None
    
    intelligence = CompanyIntelligence(api_key)
    return await intelligence.get_company_synopsis(company_data, compliance_score)