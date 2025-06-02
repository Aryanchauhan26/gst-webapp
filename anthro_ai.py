import os
import anthropic
from googlesearch import search
import httpx
from bs4 import BeautifulSoup
import asyncio
from typing import Dict, List
import re

class EnhancedAnthropicSynopsis:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def search_company_info(self, company_name: str, gstin: str) -> Dict:
        """Search web for additional company information"""
        search_results = {}
        
        # Clean company name for search
        clean_name = re.sub(r'\s*(PRIVATE|PVT|LIMITED|LTD)\.?\s*', '', company_name, flags=re.I)
        
        search_queries = [
            f"{clean_name} company profile India",
            f"{clean_name} revenue employees",
            f"{clean_name} {gstin} business",
            f"site:zaubacorp.com {clean_name}",
            f"site:linkedin.com/company {clean_name}"
        ]
        
        all_content = []
        
        async with httpx.AsyncClient() as client:
            for query in search_queries[:3]:  # Limit to 3 searches
                try:
                    # Get search results
                    urls = list(search(query, num=3, stop=3, pause=1))
                    
                    for url in urls[:2]:  # Fetch top 2 results per query
                        try:
                            response = await client.get(url, headers=self.headers, timeout=5)
                            if response.status_code == 200:
                                soup = BeautifulSoup(response.text, 'html.parser')
                                
                                # Remove script and style elements
                                for script in soup(["script", "style"]):
                                    script.decompose()
                                
                                # Get text content
                                text = soup.get_text()
                                lines = (line.strip() for line in text.splitlines())
                                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                                text = ' '.join(chunk for chunk in chunks if chunk)
                                
                                # Limit text length
                                text = text[:2000]
                                all_content.append(f"Source: {url}\nContent: {text}\n")
                                
                        except Exception:
                            continue
                            
                except Exception:
                    continue
        
        search_results['web_content'] = '\n'.join(all_content)
        return search_results

    async def get_enhanced_synopsis(self, company_data: dict) -> str:
        """Generate enhanced synopsis with web-searched data"""
        
        # Search for additional company info
        web_data = await self.search_company_info(
            company_data.get("lgnm", ""),
            company_data.get("gstin", "")
        )
        
        # Prepare enhanced data for Claude
        enhanced_prompt = f"""
        Generate a comprehensive Indian business synopsis (200-250 words) for this company.
        
        GST DATA:
        - Name: {company_data.get("lgnm")}
        - GSTIN: {company_data.get("gstin")}
        - Status: {company_data.get("sts")}
        - Registration Date: {company_data.get("rgdt")}
        - Type: {company_data.get("ctb")}
        - Compliance Score: {company_data.get("compliance", {}).get("score", 0)}%
        - Grade: {company_data.get("compliance", {}).get("grade", "N/A")}
        - Filed Returns: {company_data.get("compliance", {}).get("filed_returns", 0)}
        - Total Returns: {company_data.get("compliance", {}).get("total_returns", 0)}
        - Late Returns: {company_data.get("compliance", {}).get("late_returns", 0)}
        
        ADDITIONAL WEB INFORMATION:
        {web_data.get('web_content', 'No additional information found')}
        
        Instructions:
        1. Analyze both GST compliance data and web information
        2. Focus on business health, compliance patterns, and market presence
        3. Include insights about the company's industry position if found
        4. Assess risks and opportunities
        5. Provide actionable recommendations
        6. Use Indian business context and terminology
        """
        
        try:
            message = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=512,
                temperature=0.7,
                messages=[{"role": "user", "content": enhanced_prompt}]
            )
            return message.content[0].text.strip()
        except Exception as e:
            # Fallback to basic synopsis if enhanced fails
            return await self.get_basic_synopsis(company_data)
    
    async def get_basic_synopsis(self, company_data: dict) -> str:
        """Fallback basic synopsis without web search"""
        minimal_data = {
            "name": company_data.get("lgnm"),
            "gstin": company_data.get("gstin"),
            "status": company_data.get("sts"),
            "compliance": company_data.get("compliance", {}),
            "recent_returns": company_data.get("returns", [])[:2],
        }
        
        prompt = (
            "Generate a concise Indian business synopsis (120-200 words) focusing on "
            "compliance, age, business health, and risk. Here's the company data:\n"
            f"{minimal_data}"
        )
        
        try:
            message = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=512,
                temperature=0.5,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text.strip()
        except Exception:
            return "[Error] Unable to generate synopsis. Please check your API key."

# Export the main function for backward compatibility
async def get_anthropic_synopsis(company_data: dict) -> str:
    synopsis_generator = EnhancedAnthropicSynopsis()
    return await synopsis_generator.get_enhanced_synopsis(company_data)