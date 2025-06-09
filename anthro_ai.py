# Enhanced anthro_ai.py - Web search and AI-powered company summaries
import os
import httpx
from bs4 import BeautifulSoup
import asyncio
from typing import Dict, List, Optional
import re
import logging
import json

# Try to import various search libraries
try:
    from googlesearch import search as google_search
    HAS_GOOGLE_SEARCH = True
except ImportError:
    HAS_GOOGLE_SEARCH = False
    print("googlesearch-python not installed. Run: pip install googlesearch-python")

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def search_company_web(company_name: str, location: str = None) -> List[str]:
    """Simple web search using httpx and DuckDuckGo HTML version"""
    results = []
    
    # Clean company name
    clean_name = re.sub(r'\s*(PRIVATE|PVT|LIMITED|LTD)\.?\s*', '', company_name, flags=re.I).strip()
    
    # Search queries
    queries = [
        f"{clean_name} company profile India",
        f"{clean_name} about us",
        f"{clean_name} products services"
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for query in queries[:2]:  # Limit to 2 searches
            try:
                # Use DuckDuckGo HTML version (no API needed)
                search_url = "https://html.duckduckgo.com/html/"
                params = {"q": query, "t": "h_", "ia": "web"}
                
                response = await client.post(search_url, data=params)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract search results
                    for result in soup.find_all('a', class_='result__a')[:3]:  # Top 3 results
                        url = result.get('href', '')
                        if url and not url.startswith('/') and 'duckduckgo.com' not in url:
                            results.append(url)
                
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Search error for '{query}': {e}")
                continue
    
    return list(set(results))  # Remove duplicates

async def fetch_page_content(url: str) -> str:
    """Fetch and extract relevant content from a webpage"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = await client.get(url, headers=headers, follow_redirects=True)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "header", "footer"]):
                    script.decompose()
                
                # Extract relevant content
                content_tags = soup.find_all(['p', 'div', 'section'], limit=20)
                
                relevant_content = []
                keywords = ['about', 'company', 'business', 'service', 'product', 
                           'solution', 'industry', 'founded', 'established', 
                           'specialize', 'provide', 'offer', 'manufacture']
                
                for tag in content_tags:
                    text = tag.get_text().strip()
                    if text and len(text) > 50 and any(kw in text.lower() for kw in keywords):
                        relevant_content.append(text[:500])  # Limit length
                        if len(relevant_content) >= 5:  # Get top 5 relevant paragraphs
                            break
                
                return '\n'.join(relevant_content)
    
    except Exception as e:
        logger.warning(f"Error fetching {url}: {e}")
    
    return ""

async def search_indiamart(company_name: str) -> str:
    """Search for company on IndiaMART"""
    try:
        clean_name = re.sub(r'\s*(PRIVATE|PVT|LIMITED|LTD)\.?\s*', '', company_name, flags=re.I).strip()
        search_url = f"https://www.indiamart.com/search.html?ss={clean_name.replace(' ', '+')}"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = await client.get(search_url, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Look for company descriptions
                descriptions = soup.find_all('p', class_='desc')
                if descriptions:
                    return ' '.join([d.get_text().strip() for d in descriptions[:2]])
    except:
        pass
    
    return ""

async def get_company_info_from_web(company_name: str, gstin: str = None, location: str = None) -> Dict[str, str]:
    """Gather company information from web sources"""
    info = {
        'web_content': '',
        'sources': []
    }
    
    try:
        # Search for URLs
        urls = await search_company_web(company_name, location)
        
        # Also search IndiaMART
        indiamart_info = await search_indiamart(company_name)
        if indiamart_info:
            info['web_content'] += f"\n\nFrom IndiaMART: {indiamart_info}"
            info['sources'].append('IndiaMART')
        
        # Fetch content from found URLs
        all_content = []
        for url in urls[:3]:  # Limit to top 3 URLs
            content = await fetch_page_content(url)
            if content:
                all_content.append(f"Source: {url}\n{content}")
                info['sources'].append(url)
        
        if all_content:
            info['web_content'] += '\n\n'.join(all_content)
        
        # If no web content found, try Google Search if available
        if not info['web_content'] and HAS_GOOGLE_SEARCH:
            try:
                clean_name = re.sub(r'\s*(PRIVATE|PVT|LIMITED|LTD)\.?\s*', '', company_name, flags=re.I).strip()
                search_results = list(google_search(f"{clean_name} company India", num=3, stop=3))
                
                for url in search_results:
                    content = await fetch_page_content(url)
                    if content:
                        info['web_content'] += f"\n\nSource: {url}\n{content}"
                        info['sources'].append(url)
            except Exception as e:
                logger.warning(f"Google search failed: {e}")
        
    except Exception as e:
        logger.error(f"Web search error: {e}")
    
    return info

async def get_anthropic_synopsis(company_data: Dict) -> Optional[str]:
    """
    Generate a comprehensive business overview using web research and AI.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set - using fallback synopsis")
        return await generate_web_based_synopsis(company_data)
    
    try:
        # Gather web information
        web_info = await get_company_info_from_web(
            company_data.get('lgnm', ''),
            company_data.get('gstin', ''),
            company_data.get('adr', '')
        )
        
        # Extract key data
        nba = company_data.get('nba', [])
        nba_str = ', '.join(nba) if nba else 'Not specified'
        
        stj = company_data.get('stj', '')
        state = 'N/A'
        if stj and 'State - ' in stj:
            state = stj.split('State - ')[1].split(',')[0]
        
        # Count returns filed
        returns = company_data.get('returns', [])
        gstr1_count = len([r for r in returns if r.get('rtntype') == 'GSTR1'])
        gstr3b_count = len([r for r in returns if r.get('rtntype') == 'GSTR3B'])
        
        prompt = f"""
        You are a business analyst. Write a comprehensive business overview for this Indian company based on web research.
        
        COMPANY GST DATA:
        - Legal Name: {company_data.get("lgnm")}
        - Trade Name: {company_data.get("tradeName", "")}
        - GSTIN: {company_data.get("gstin")}
        - Business Type: {company_data.get("ctb", "")}
        - Nature of Business: {nba_str}
        - Registration Date: {company_data.get("rgdt", "")}
        - Location: {company_data.get("adr", "")}
        - State: {state}
        - Company Category: {company_data.get("compCategory", "")}
        - GST Returns Filed: {len(returns)} total ({gstr1_count} GSTR-1, {gstr3b_count} GSTR-3B)
        
        WEB RESEARCH FINDINGS:
        {web_info.get('web_content', 'No web information found')}
        
        Sources consulted: {', '.join(web_info.get('sources', [])) if web_info.get('sources') else 'No web sources available'}
        
        INSTRUCTIONS:
        Write a 100-150 word business overview that includes:
        1. What the company actually does (products/services/industry) based on web research
        2. Company's market presence and business operations
        3. Any notable clients, projects, or achievements found online
        4. Business scale and operational insights
        
        If web research found specific information about the company, prioritize that over generic descriptions.
        If no specific web information was found, make intelligent inferences based on the company name and business type.
        
        Focus on providing actionable business intelligence, not just restating GST data.
        """
        
        if AsyncAnthropic:
            client = AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=400,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            if hasattr(response, "content") and len(response.content) > 0:
                return response.content[0].text.strip()
    
    except Exception as e:
        logger.error(f"AI synopsis generation error: {e}")
    
    # Fallback to web-based synopsis without AI
    return await generate_web_based_synopsis(company_data, web_info if 'web_info' in locals() else None)

async def generate_web_based_synopsis(company_data: Dict, web_info: Dict = None) -> str:
    """Generate synopsis based on web research without AI"""
    
    if not web_info:
        web_info = await get_company_info_from_web(
            company_data.get('lgnm', ''),
            company_data.get('gstin', ''),
            company_data.get('adr', '')
        )
    
    company_name = company_data.get("lgnm", "Unknown Company")
    company_type = company_data.get("ctb", "")
    location = company_data.get("adr", "")
    reg_date = company_data.get("rgdt", "")
    nba = company_data.get('nba', [])
    category = company_data.get("compCategory", "")
    
    # Extract location
    location_parts = location.split(',') if location else []
    city = location_parts[0].strip() if location_parts else 'India'
    
    # Start building synopsis
    synopsis_parts = []
    
    # Introduction
    synopsis_parts.append(f"{company_name} is a {company_type} ")
    
    # Add business type from NBA
    if nba:
        synopsis_parts.append(f"operating as a {', '.join(nba).lower()}. ")
    else:
        synopsis_parts.append("engaged in business operations. ")
    
    # Add establishment info
    if reg_date:
        try:
            year = reg_date.split('/')[-1]
            synopsis_parts.append(f"Established in {year}, ")
        except:
            pass
    
    # Add web findings if available
    if web_info.get('web_content'):
        # Extract key sentences from web content
        web_content = web_info['web_content']
        
        # Look for product/service mentions
        product_keywords = ['manufactur', 'produc', 'provid', 'offer', 'speciali', 'serv', 'solution', 'supply']
        relevant_sentences = []
        
        for sentence in web_content.split('.'):
            if any(keyword in sentence.lower() for keyword in product_keywords):
                clean_sentence = sentence.strip()
                if 20 < len(clean_sentence) < 200:  # Reasonable sentence length
                    relevant_sentences.append(clean_sentence)
        
        if relevant_sentences:
            synopsis_parts.append("Based on available information, the company ")
            synopsis_parts.append(relevant_sentences[0].lower() + ". ")
            if len(relevant_sentences) > 1:
                synopsis_parts.append(relevant_sentences[1] + ". ")
    else:
        # Generic business description based on name/type
        name_lower = company_name.lower()
        
        if any(word in name_lower for word in ['tech', 'software', 'infotech', 'solutions']):
            synopsis_parts.append("the company likely provides technology and software solutions. ")
        elif any(word in name_lower for word in ['trading', 'exports', 'imports']):
            synopsis_parts.append("the company appears to be involved in trading and distribution. ")
        elif any(word in name_lower for word in ['manufactur', 'industries', 'engineer']):
            synopsis_parts.append("the company is likely engaged in manufacturing operations. ")
        else:
            synopsis_parts.append("the company provides business services in its sector. ")
    
    # Add location and operational info
    synopsis_parts.append(f"Operating from {city}, ")
    
    # Add compliance info
    returns = company_data.get('returns', [])
    if returns:
        synopsis_parts.append(f"the company maintains active GST compliance with {len(returns)} returns filed. ")
    else:
        synopsis_parts.append("the company is registered for GST. ")
    
    # Add category info
    if category:
        synopsis_parts.append(f"Classified as a '{category}' category business, ")
    
    # Closing
    synopsis_parts.append(f"the company continues to operate in the {city} region serving its customer base.")
    
    # Add source note if web info was found
    if web_info.get('sources'):
        synopsis_parts.append(f" (Information compiled from web sources including {web_info['sources'][0] if web_info['sources'] else 'public records'})")
    
    return ''.join(synopsis_parts)

# For backward compatibility
class EnhancedAnthropicSynopsis:
    def __init__(self):
        pass
    
    async def get_enhanced_synopsis(self, company_data: dict) -> str:
        """Wrapper method for compatibility"""
        synopsis = await get_anthropic_synopsis(company_data)
        return synopsis or "Company information not available"