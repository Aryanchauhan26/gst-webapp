# Enhanced anthro_ai.py - AI-powered company analysis
<<<<<<< HEAD
=======

>>>>>>> c532489b53e866b4caaacf4b11866da31089f9c3
import os
import asyncio
<<<<<<< HEAD
import re
import logging
import json
from typing import Dict, List, Optional

try:
    from googlesearch import search as google_search
    HAS_GOOGLE_SEARCH = True
except ImportError:
    HAS_GOOGLE_SEARCH = False
=======
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
>>>>>>> c532489b53e866b4caaacf4b11866da31089f9c3

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️  Anthropic library not installed. AI features will use fallback.")

<<<<<<< HEAD
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
=======
# Setup logging
logger = logging.getLogger(__name__)

# Get API key from environment
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

class GSTAnalysisAI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.client = None
        
        if self.api_key and ANTHROPIC_AVAILABLE:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("✅ Anthropic AI client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Anthropic client: {e}")
                self.client = None
        else:
            logger.warning("⚠️  AI features running in fallback mode")

    async def analyze_company_comprehensive(self, company_data: Dict) -> Dict:
        """Comprehensive company analysis using AI"""
        try:
            if self.client:
                return await self._ai_analysis(company_data)
            else:
                return self._fallback_analysis(company_data)
        except Exception as e:
            logger.error(f"Error in company analysis: {e}")
            return self._fallback_analysis(company_data)

    async def _ai_analysis(self, company_data: Dict) -> Dict:
        """AI-powered analysis using Anthropic"""
        try:
            # Prepare company data for AI analysis
            analysis_prompt = self._build_analysis_prompt(company_data)
            
            # Call Anthropic API
            message = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-sonnet-20240229",
                max_tokens=1500,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": analysis_prompt
                }]
            )
            
            # Parse AI response
            ai_response = message.content[0].text
            return self._parse_ai_response(ai_response, company_data)
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._fallback_analysis(company_data)

    def _build_analysis_prompt(self, company_data: Dict) -> str:
        """Build comprehensive analysis prompt for AI"""
        company_name = company_data.get('lgnm', 'Unknown Company')
        gstin = company_data.get('gstin', 'N/A')
        status = company_data.get('sts', 'Unknown')
        registration_date = company_data.get('rgdt', 'N/A')
        
        # Extract business details
        business_nature = company_data.get('nba', [])
        filing_status = company_data.get('filing_status', {})
        compliance_score = company_data.get('compliance_score', 0)
        
        prompt = f"""
As a GST compliance expert, analyze this Indian company's GST data and provide insights:

**Company Details:**
- Name: {company_name}
- GSTIN: {gstin}
- Status: {status}
- Registration Date: {registration_date}
- Business Activities: {', '.join(business_nature) if business_nature else 'Not specified'}

**Compliance Data:**
- Current Compliance Score: {compliance_score}%
- Filing Status: {json.dumps(filing_status, indent=2)}

**Analysis Required:**
1. **Risk Assessment** (High/Medium/Low) with reasoning
2. **Compliance Insights** - Key strengths and concerns
3. **Business Recommendations** - Actionable advice
4. **Red Flags** - Any concerning patterns
5. **Overall Synopsis** - 2-3 sentence summary

**Response Format (JSON):**
```json
{{
    "risk_level": "High/Medium/Low",
    "risk_score": 0-100,
    "synopsis": "Brief 2-3 sentence summary",
    "strengths": ["strength1", "strength2"],
    "concerns": ["concern1", "concern2"],
    "recommendations": ["rec1", "rec2"],
    "red_flags": ["flag1", "flag2"],
    "confidence_level": 0-100
}}
```

Provide practical, actionable insights based on GST compliance patterns.
        """
        
        return prompt

    def _parse_ai_response(self, ai_response: str, company_data: Dict) -> Dict:
        """Parse and structure AI response"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'```json\n(.*?)\n```', ai_response, re.DOTALL)
            
            if json_match:
                parsed_data = json.loads(json_match.group(1))
            else:
                # Fallback parsing if JSON not found
                parsed_data = self._extract_insights_from_text(ai_response)
            
            # Ensure all required fields
            analysis = {
                "risk_level": parsed_data.get("risk_level", "Medium"),
                "risk_score": parsed_data.get("risk_score", 50),
                "synopsis": parsed_data.get("synopsis", "Analysis completed successfully."),
                "strengths": parsed_data.get("strengths", []),
                "concerns": parsed_data.get("concerns", []),
                "recommendations": parsed_data.get("recommendations", []),
                "red_flags": parsed_data.get("red_flags", []),
                "confidence_level": parsed_data.get("confidence_level", 75),
                "analysis_date": datetime.now().isoformat(),
                "source": "AI Analysis"
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return self._fallback_analysis(company_data)

    def _extract_insights_from_text(self, text: str) -> Dict:
        """Extract insights from unstructured AI response"""
        insights = {
            "risk_level": "Medium",
            "risk_score": 50,
            "synopsis": "AI analysis completed.",
            "strengths": [],
            "concerns": [],
            "recommendations": [],
            "red_flags": [],
            "confidence_level": 60
        }
        
        # Simple text parsing logic
        text_lower = text.lower()
        
        # Determine risk level
        if any(word in text_lower for word in ['high risk', 'critical', 'severe', 'warning']):
            insights["risk_level"] = "High"
            insights["risk_score"] = 80
        elif any(word in text_lower for word in ['low risk', 'good', 'excellent', 'compliant']):
            insights["risk_level"] = "Low"
            insights["risk_score"] = 30
        
        # Extract synopsis (first meaningful sentence)
        sentences = text.split('.')
        for sentence in sentences:
            if len(sentence.strip()) > 20:
                insights["synopsis"] = sentence.strip() + "."
                break
        
        return insights

    def _fallback_analysis(self, company_data: Dict) -> Dict:
        """Fallback analysis when AI is not available"""
        company_name = company_data.get('lgnm', 'Unknown Company')
        status = company_data.get('sts', 'Unknown')
        compliance_score = company_data.get('compliance_score', 0)
        
        # Rule-based analysis
        if compliance_score >= 80:
            risk_level = "Low"
            risk_score = 25
            synopsis = f"{company_name} shows strong GST compliance with a score of {compliance_score}%."
            strengths = ["High compliance score", "Good filing record"]
            concerns = []
            recommendations = ["Maintain current compliance standards"]
        elif compliance_score >= 60:
            risk_level = "Medium"
            risk_score = 50
            synopsis = f"{company_name} has moderate GST compliance. Some improvements recommended."
            strengths = ["Acceptable compliance level"]
            concerns = ["Room for compliance improvement"]
            recommendations = ["Review filing processes", "Consider compliance automation"]
        else:
            risk_level = "High"
            risk_score = 75
            synopsis = f"{company_name} shows concerning GST compliance patterns requiring attention."
            strengths = []
            concerns = ["Low compliance score", "Potential filing issues"]
            recommendations = ["Immediate compliance review required", "Consider professional consultation"]
        
        # Check status-based insights
        red_flags = []
        if status.lower() in ['cancelled', 'suspended']:
            red_flags.append(f"Company status is {status}")
            risk_score = min(risk_score + 20, 95)
        
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "synopsis": synopsis,
            "strengths": strengths,
            "concerns": concerns,
            "recommendations": recommendations,
            "red_flags": red_flags,
            "confidence_level": 85,
            "analysis_date": datetime.now().isoformat(),
            "source": "Rule-based Analysis"
        }

# Global AI instance
ai_analyzer = GSTAnalysisAI()

async def get_anthropic_synopsis(company_data: Dict) -> str:
    """Main function called from main.py - returns synopsis"""
    try:
        analysis = await ai_analyzer.analyze_company_comprehensive(company_data)
        return analysis.get("synopsis", "Analysis completed successfully.")
    except Exception as e:
        logger.error(f"Error getting synopsis: {e}")
        company_name = company_data.get('lgnm', 'Unknown Company')
        return f"Basic analysis completed for {company_name}. Manual review recommended."

async def get_comprehensive_analysis(company_data: Dict) -> Dict:
    """Get complete AI analysis - for detailed reports"""
    return await ai_analyzer.analyze_company_comprehensive(company_data)

def analyze_late_filings(returns_data: List) -> Dict:
    """Analyze late filing patterns"""
    if not returns_data:
        return {
            "total_returns": 0,
            "late_filings": 0,
            "late_filing_percentage": 0,
            "pattern": "No filing data available",
            "risk_indicator": "Unknown"
        }
    
    total_returns = len(returns_data)
    late_count = 0
    
    for return_data in returns_data:
        # Check if filing was late (simplified logic)
        due_date = return_data.get('due_date')
        filed_date = return_data.get('filed_date')
        
        if due_date and filed_date:
            try:
                due = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                filed = datetime.fromisoformat(filed_date.replace('Z', '+00:00'))
                if filed > due:
                    late_count += 1
            except:
                continue
    
    late_percentage = (late_count / total_returns * 100) if total_returns > 0 else 0
    
    # Determine pattern and risk
    if late_percentage >= 50:
        pattern = "Concerning pattern of late filings"
        risk_indicator = "High"
    elif late_percentage >= 25:
        pattern = "Moderate late filing pattern"
        risk_indicator = "Medium"
    elif late_percentage > 0:
        pattern = "Occasional late filings"
        risk_indicator = "Low"
    else:
        pattern = "Consistent timely filings"
        risk_indicator = "Very Low"
    
    return {
        "total_returns": total_returns,
        "late_filings": late_count,
        "late_filing_percentage": round(late_percentage, 2),
        "pattern": pattern,
        "risk_indicator": risk_indicator
    }

# Test function
async def test_ai_analysis():
    """Test the AI analysis functionality"""
    sample_company_data = {
        "lgnm": "Test Company Private Limited",
        "gstin": "27AABCU9603R1ZX",
        "sts": "Active",
        "rgdt": "2020-01-15",
        "nba": ["Wholesale of computer hardware", "Software development"],
        "compliance_score": 75,
        "filing_status": {
            "gstr1_filed": True,
            "gstr3b_filed": True,
            "annual_return_filed": False
        }
    }
    
    print("🧪 Testing AI Analysis...")
    analysis = await get_comprehensive_analysis(sample_company_data)
    print("✅ Analysis completed:")
    print(json.dumps(analysis, indent=2))

if __name__ == "__main__":
    asyncio.run(test_ai_analysis())
>>>>>>> c532489b53e866b4caaacf4b11866da31089f9c3
