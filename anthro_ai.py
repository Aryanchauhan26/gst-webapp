# Fixed anthro_ai.py - Focus on company business overview
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
        """Search web for company business information"""
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
                    urls = list(search(query, num=3, stop=3, pause=1))
                    
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
                                    if text and any(keyword in text.lower() for keyword in business_keywords):
                                        if clean_name.lower() in text.lower():
                                            relevant_text.append(text[:500])  # Limit each paragraph
                                
                                if relevant_text:
                                    content = f"Source: {url}\n"
                                    content += '\n'.join(relevant_text[:3])  # Top 3 relevant paragraphs
                                    all_content.append(content)
                                
                        except Exception:
                            continue
                            
                except Exception:
                    continue
        
        search_results['web_content'] = '\n\n'.join(all_content)
        return search_results

    async def get_enhanced_synopsis(self, company_data: dict) -> str:
        """Generate company business overview"""
        
        # Search for company business information
        web_data = await self.search_company_info(
            company_data.get("lgnm", ""),
            company_data.get("gstin", "")
        )
        
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
            return message.content[0].text.strip()
        except Exception as e:
            # Fallback synopsis focused on business
            return self.generate_fallback_business_synopsis(company_data)
    
    def generate_fallback_business_synopsis(self, company_data: dict) -> str:
        """Generate business-focused synopsis without API"""
        company_name = company_data.get("lgnm", "Unknown Company")
        company_type = company_data.get("ctb", "")
        location = company_data.get("adr", "")
        
        # Try to infer business from name
        name_lower = company_name.lower()
        
        if any(word in name_lower for word in ['tech', 'software', 'infotech', 'solutions']):
            business_type = "technology and software solutions"
        elif any(word in name_lower for word in ['trading', 'exports', 'imports']):
            business_type = "trading and import/export"
        elif any(word in name_lower for word in ['manufacturing', 'industries', 'products']):
            business_type = "manufacturing"
        elif any(word in name_lower for word in ['services', 'consultancy', 'consulting']):
            business_type = "professional services"
        else:
            business_type = "business operations"
        
        synopsis = f"{company_name} is a {company_type} engaged in {business_type}. "
        synopsis += f"The company operates from {location.split(',')[0] if location else 'India'}. "
        synopsis += "Specific details about the company's products, services, and market position "
        synopsis += "require further research. The company maintains its GST registration and "
        synopsis += "compliance obligations as per Indian tax regulations."
        
        return synopsis

# Export the main function
async def get_anthropic_synopsis(company_data: dict) -> str:
    synopsis_generator = EnhancedAnthropicSynopsis()
    return await synopsis_generator.get_enhanced_synopsis(company_data)
