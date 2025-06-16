# Enhanced anthro_ai.py - AI-powered company analysis
import os
import httpx
from bs4 import BeautifulSoup
import asyncio
import re
import logging
import json
from typing import Dict, List, Optional

try:
    from googlesearch import search as google_search
    HAS_GOOGLE_SEARCH = True
except ImportError:
    HAS_GOOGLE_SEARCH = False

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def search_company_web(company_name: str, location: str = None) -> List[str]:
    """Search for company information using DuckDuckGo"""
    results = []
    clean_name = re.sub(r'\s*(PRIVATE|PVT|LIMITED|LTD)\.?\s*', '', company_name, flags=re.I).strip()
    
    queries = [
        f"{clean_name} company profile India",
        f"{clean_name} about us products services"
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for query in queries[:2]:
            try:
                search_url = "https://html.duckduckgo.com/html/"
                params = {"q": query, "t": "h_", "ia": "web"}
                response = await client.post(search_url, data=params)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for result in soup.find_all('a', class_='result__a')[:3]:
                        url = result.get('href', '')
                        if url and not url.startswith('/') and 'duckduckgo.com' not in url:
                            results.append(url)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"Search error for '{query}': {e}")
                continue
    
    return list(set(results))

async def fetch_page_content(url: str) -> str:
    """Fetch and extract relevant content from a webpage"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = await client.get(url, headers=headers, follow_redirects=True)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for script in soup(["script", "style", "nav", "header", "footer"]):
                    script.decompose()
                
                content_tags = soup.find_all(['p', 'div', 'section'], limit=20)
                relevant_content = []
                keywords = ['about', 'company', 'business', 'service', 'product', 
                           'solution', 'industry', 'founded', 'established', 
                           'specialize', 'provide', 'offer', 'manufacture']
                
                for tag in content_tags:
                    text = tag.get_text().strip()
                    if text and len(text) > 50 and any(kw in text.lower() for kw in keywords):
                        relevant_content.append(text[:500])
                        if len(relevant_content) >= 5:
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
                descriptions = soup.find_all('p', class_='desc')
                if descriptions:
                    return ' '.join([d.get_text().strip() for d in descriptions[:2]])
    except:
        pass
    
    return ""

async def get_company_info_from_web(company_name: str, gstin: str = None, location: str = None) -> Dict[str, str]:
    """Gather company information from web sources"""
    info = {'web_content': '', 'sources': []}
    
    try:
        urls = await search_company_web(company_name, location)
        
        indiamart_info = await search_indiamart(company_name)
        if indiamart_info:
            info['web_content'] += f"\n\nFrom IndiaMART: {indiamart_info}"
            info['sources'].append('IndiaMART')
        
        all_content = []
        for url in urls[:3]:
             = await fetch_page_content(url)
            if content:
                all_content.append(f"Source: {url}\n{content}")
                info['sources'].append(url)
        
        if all_content:
            info['web_content'] += '\n\n'.join(all_content)
        
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
    """Generate a concise business overview using AI"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set - using fallback synopsis")
        return await generate_fallback_synopsis(company_data)
    
    try:
        company_name = company_data.get('lgnm', '')
        nba = company_data.get('nba', [])
        nba_str = ', '.join(nba[:2]) if nba else 'Business services'
        
        state = 'India'
        if company_data.get('stj') and 'State - ' in company_data.get('stj'):
            state = company_data.get('stj').split('State - ')[1].split(',')[0]
        
        returns = company_data.get('returns', [])
        compliance_status = "Strong compliance" if len(returns) > 10 else "Active"
        
        prompt = f"""
        Write a single paragraph (max 280 characters) describing this company:
        - Name: {company_name}
        - Business: {nba_str}
        - Location: {state}
        - Status: {compliance_status}
        
        Make it informative and professional. Include what they do and their key strength.
        Must be under 280 characters.
        """
        
        if AsyncAnthropic:
            client = AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            if hasattr(response, "content") and len(response.content) > 0:
                synopsis = response.content[0].text.strip()
                if len(synopsis) > 280:
                    synopsis = synopsis[:277] + "..."
                return synopsis
    
    except Exception as e:
        logger.error(f"AI synopsis generation error: {e}")
    
    return await generate_fallback_synopsis(company_data)

async def generate_fallback_synopsis(company_data: Dict) -> str:
    """Generate synopsis without AI"""
    company_name = company_data.get("lgnm", "Unknown Company")
    nba = company_data.get('nba', [])
    state = 'India'
    if company_data.get('stj') and 'State - ' in company_data.get('stj'):
        state = company_data.get('stj').split('State - ')[1].split(',')[0]
    
    if nba:
        activity = nba[0].lower()
        synopsis = f"{company_name} is a {activity} company based in {state}."
    else:
        synopsis = f"{company_name} is a business services company based in {state}."
    
    returns = company_data.get('returns', [])
    if len(returns) > 20 and len(synopsis) < 200:
        synopsis += f" With {len(returns)} GST returns filed, they maintain strong tax compliance."
    elif len(returns) > 10 and len(synopsis) < 220:
        synopsis += f" Active GST filer with {len(returns)} returns."
    
    if company_data.get('rgdt') and len(synopsis) < 240:
        try:
            year = company_data.get('rgdt').split('/')[-1]
            synopsis += f" Established {year}."
        except:
            pass
    
    if len(synopsis) > 280:
        synopsis = synopsis[:277] + "..."
    
    return synopsis

# For backward compatibility
class EnhancedAnthropicSynopsis:
    def __init__(self):
        pass
    
    async def get_enhanced_synopsis(self, company_data: dict) -> str:
        synopsis = await get_anthropic_synopsis(company_data)
        return synopsis or "Company information not available"