from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Tuple
from collections import defaultdict
import httpx
import os
import re
from pathlib import Path

from weasyprint import HTML
from fastapi.concurrency import run_in_threadpool
from anthro_ai import get_anthropic_synopsis

def validate_gstin(gstin: str) -> Tuple[bool, str]:
    """Validate GSTIN format"""
    try:
        if not gstin:
            return False, "GSTIN cannot be empty"
        gstin = gstin.strip().upper()
        if len(gstin) != 15:
            return False, f"GSTIN must be 15 characters long, got {len(gstin)}"
        if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$', gstin):
            return False, "Invalid GSTIN format."
        state_code = int(gstin[:2])
        if state_code < 1 or state_code > 37:
            return False, f"Invalid state code: {state_code}"
        return True, "Valid GSTIN"
    except Exception as e:
        return False, f"GSTIN validation error: {str(e)}"

class GSAPIClient:
    """Client for GST API"""
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key
        self.host = host
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host,
            "User-Agent": "GST-Compliance-Platform/2.0"
        }
    
    async def fetch_gstin_data(self, gstin: str) -> Dict:
        """Fetch GSTIN data from API"""
        url = f"https://{self.host}/free/gstin/{gstin}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        if not data.get("success", False):
            raise HTTPException(status_code=400, detail=f"API Error: {data.get('message', 'Unknown error')}")
        return data.get("data", {})

# Fixed late returns calculation in main.py
def mark_late_returns(returns: List[Dict]) -> List[Dict]:
    """Mark returns as late based on due dates - FIXED VERSION"""
    for ret in returns:
        ret['late'] = False
        dof = ret.get("dof")
        fy = ret.get("fy")
        month_str = ret.get("taxp")
        rtntype = ret.get("rtntype", "") or ret.get("rtype", "")
        
        if fy and month_str and dof:
            try:
                # Parse financial year correctly
                if "-" in fy:
                    start_year = int(fy.split("-")[0])
                else:
                    start_year = int(fy[:4]) if len(fy) >= 4 else int(fy)
                
                # Month mapping for Indian financial year (April to March)
                month_map = {
                    "April": (4, start_year),
                    "May": (5, start_year),
                    "June": (6, start_year),
                    "July": (7, start_year),
                    "August": (8, start_year),
                    "September": (9, start_year),
                    "October": (10, start_year),
                    "November": (11, start_year),
                    "December": (12, start_year),
                    "January": (1, start_year + 1),
                    "February": (2, start_year + 1),
                    "March": (3, start_year + 1)
                }
                
                month_info = month_map.get(month_str)
                if month_info:
                    month, year = month_info
                    
                    # Due dates based on return type
                    if rtntype.upper() in ['GSTR1', 'GSTR-1']:
                        # GSTR-1 due on 11th of next month
                        if month == 12:
                            due_date = datetime(year + 1, 1, 11)
                        else:
                            due_date = datetime(year, month + 1, 11)
                    elif rtntype.upper() in ['GSTR3B', 'GSTR-3B']:
                        # GSTR-3B due on 20th of next month
                        if month == 12:
                            due_date = datetime(year + 1, 1, 20)
                        else:
                            due_date = datetime(year, month + 1, 20)
                    else:
                        # Default to 20th for other returns
                        if month == 12:
                            due_date = datetime(year + 1, 1, 20)
                        else:
                            due_date = datetime(year, month + 1, 20)
                    
                    # Parse filed date
                    filed_date = datetime.strptime(dof, "%d/%m/%Y")
                    
                    # Check if late
                    if filed_date > due_date:
                        ret['late'] = True
                        # Add days late for reference
                        ret['days_late'] = (filed_date - due_date).days
                    else:
                        ret['days_late'] = 0
                        
            except Exception as e:
                # Log error but don't crash
                print(f"Error processing return: {e}")
                ret['late'] = False
                ret['days_late'] = 0
                
    return returns

def calculate_compliance_score(data: Dict) -> Dict:
    """Calculate enhanced compliance score"""
    returns = data.get('returns', [])
    if not returns:
        return {
            'score': 0,
            'grade': 'N/A',
            'status': 'No Returns Found',
            'total_returns': 0,
            'filed_returns': 0,
            'pending_returns': 0,
            'late_returns': 0,
            'details': 'No return filing history available'
        }
    
    filed_count = sum(1 for ret in returns if ret.get("dof"))
    late_count = sum(1 for ret in returns if ret.get('late'))
    total_count = len(returns)
    on_time_count = filed_count - late_count
    
    score = round(((on_time_count + 0.5 * late_count) / total_count) * 100, 1)
    
    # Grade calculation
    if score >= 95:
        grade = 'A+'
    elif score >= 85:
        grade = 'A'
    elif score >= 75:
        grade = 'B'
    elif score >= 60:
        grade = 'C'
    else:
        grade = 'D'
    
    # Status determination
    if score >= 90:
        status = 'Excellent Compliance'
    elif score >= 75:
        status = 'Good Compliance'
    elif score >= 60:
        status = 'Fair Compliance'
    else:
        status = 'Poor Compliance'
    
    return {
        'score': score,
        'grade': grade,
        'status': status,
        'total_returns': total_count,
        'filed_returns': filed_count,
        'pending_returns': total_count - filed_count,
        'late_returns': late_count,
        'details': f'Filed {filed_count} out of {total_count} returns, {late_count} late'
    }

def organize_returns_by_year(returns: List[Dict]) -> Dict:
    """Organize returns by financial year"""
    returns_by_year = defaultdict(list)
    for ret in returns:
        fy = ret.get('fy')
        if fy:
            returns_by_year[fy].append(ret)
    return dict(sorted(returns_by_year.items(), reverse=True))

def generate_synopsis(data: Dict) -> Dict:
    """Generate company synopsis from GST data"""
    synopsis = {
        'business_profile': {},
        'operational_insights': {},
        'compliance_summary': {},
        'risk_assessment': {},
        'key_metrics': {}
    }
    
    # Business Profile
    company_name = data.get('lgnm', 'Unknown Company')
    trade_name = data.get('tradeName', '')
    registration_date = data.get('rgdt', '')
    company_type = data.get('ctb', '')
    status = data.get('sts', '')
    gstin = data.get('gstin', '')
    
    # Calculate business age
    business_age = "Unknown"
    if registration_date:
        try:
            reg_date = datetime.strptime(registration_date, "%d/%m/%Y")
            age_days = (datetime.now() - reg_date).days
            years = age_days // 365
            months = (age_days % 365) // 30
            if years > 0:
                business_age = f"{years} year{'s' if years > 1 else ''}"
                if months > 0:
                    business_age += f", {months} month{'s' if months > 1 else ''}"
            else:
                business_age = f"{months} month{'s' if months > 1 else ''}"
        except:
            pass
    
    # State mapping
    state_map = {
        '01': 'Jammu & Kashmir', '02': 'Himachal Pradesh', '03': 'Punjab',
        '04': 'Chandigarh', '05': 'Uttarakhand', '06': 'Haryana',
        '07': 'Delhi', '08': 'Rajasthan', '09': 'Uttar Pradesh',
        '10': 'Bihar', '11': 'Sikkim', '12': 'Arunachal Pradesh',
        '13': 'Nagaland', '14': 'Manipur', '15': 'Mizoram',
        '16': 'Tripura', '17': 'Meghalaya', '18': 'Assam',
        '19': 'West Bengal', '20': 'Jharkhand', '21': 'Odisha',
        '22': 'Chhattisgarh', '23': 'Madhya Pradesh', '24': 'Gujarat',
        '25': 'Daman & Diu', '26': 'Dadra & Nagar Haveli', '27': 'Maharashtra',
        '28': 'Andhra Pradesh', '29': 'Karnataka', '30': 'Goa',
        '31': 'Lakshadweep', '32': 'Kerala', '33': 'Tamil Nadu',
        '34': 'Puducherry', '35': 'Andaman & Nicobar', '36': 'Telangana',
        '37': 'Andhra Pradesh'
    }
    
    state_code = gstin[:2] if gstin else ''
    state_name = state_map.get(state_code, 'Unknown')
    
    synopsis['business_profile'] = {
        'display_name': trade_name if trade_name and trade_name != company_name else company_name,
        'legal_name': company_name,
        'business_age': business_age,
        'entity_type': company_type or 'Unknown',
        'operational_status': status,
        'state': state_name,
        'state_code': state_code,
        'jurisdiction': data.get('stj', 'Unknown')
    }
    
    # Operational Insights
    returns = data.get('returns', [])
    compliance = data.get('compliance', {})
    
    filing_consistency = "No filing history"
    recent_activity = "No recent activity"
    returns_filed = 0
    total_returns_due = len(returns)
    
    if returns:
        filed_returns = [r for r in returns if r.get('dof')]
        returns_filed = len(filed_returns)
        filing_rate = returns_filed / len(returns) if returns else 0
        
        if filing_rate >= 0.95:
            filing_consistency = "Highly consistent filer"
        elif filing_rate >= 0.8:
            filing_consistency = "Regular filer"
        elif filing_rate >= 0.6:
            filing_consistency = "Moderate filer"
        else:
            filing_consistency = "Irregular filer"
        
        recent_returns = sorted(returns, key=lambda x: (x.get('fy', ''), x.get('taxp', '')), reverse=True)[:3]
        filed_recent = sum(1 for r in recent_returns if r.get('dof'))
        
        if filed_recent == len(recent_returns):
            recent_activity = "Active and compliant"
        elif filed_recent > 0:
            recent_activity = "Partially active"
        else:
            recent_activity = "Inactive filing"
    
    return_types = set()
    for ret in returns:
        ret_type = ret.get('rtype') or ret.get('rtntype', '')
        if ret_type:
            return_types.add(ret_type)
    
    synopsis['operational_insights'] = {
        'filing_consistency': filing_consistency,
        'recent_activity': recent_activity,
        'return_types': sorted(list(return_types)),
        'total_returns_due': total_returns_due,
        'returns_filed': returns_filed
    }
    
    # Compliance Summary
    score = compliance.get('score', 0)
    grade = compliance.get('grade', 'N/A')
    late_returns = sum(1 for r in returns if r.get('late'))
    total_filed = sum(1 for r in returns if r.get('dof'))
    
    filing_reliability = "Unknown"
    if total_filed > 0:
        late_percentage = (late_returns / total_filed) * 100
        if late_percentage == 0:
            filing_reliability = "Always on time"
        elif late_percentage <= 10:
            filing_reliability = "Mostly on time"
        elif late_percentage <= 25:
            filing_reliability = "Occasionally late"
        else:
            filing_reliability = "Frequently late"
    
    synopsis['compliance_summary'] = {
        'overall_rating': grade,
        'compliance_score': score,
        'filing_reliability': filing_reliability,
        'late_filing_rate': f"{(late_returns/total_filed*100):.1f}%" if total_filed > 0 else "N/A"
    }
    
    # Risk Assessment
    compliance_risk = "Unknown"
    if score >= 90:
        compliance_risk = "Low Risk"
    elif score >= 75:
        compliance_risk = "Medium Risk"
    elif score >= 60:
        compliance_risk = "High Risk"
    else:
        compliance_risk = "Very High Risk"
    
    red_flags = []
    if status and status.lower() == 'cancelled':
        red_flags.append("GST registration cancelled")
    if score < 60:
        red_flags.append("Low compliance score")
    if total_filed > 0 and (late_returns / total_filed) > 0.3:
        red_flags.append("High rate of late filings")
    if returns and not any(r.get('dof') for r in sorted(returns, key=lambda x: (x.get('fy', ''), x.get('taxp', '')), reverse=True)[:3]):
        red_flags.append("No recent return filings")
    
    risk_level = 'High' if len(red_flags) > 2 else 'Medium' if len(red_flags) > 0 else 'Low'
    
    synopsis['risk_assessment'] = {
        'compliance_risk': compliance_risk,
        'red_flags': red_flags,
        'risk_level': risk_level
    }
    
    # Key Metrics
    synopsis['key_metrics'] = {
        'business_age_years': int(business_age.split()[0]) if business_age != "Unknown" and business_age.split()[0].isdigit() else 0,
        'filing_percentage': f"{returns_filed / total_returns_due * 100:.1f}%" if total_returns_due else "0%",
        'compliance_grade': grade,
        'total_late_returns': late_returns,
        'active_status': status == 'Active'
    }
    
    return synopsis

# Additional helper functions for advanced analytics
def generate_filing_trends(returns: List[Dict]) -> Dict:
    """Analyze filing trends over time"""
    if not returns:
        return {'trend': 'No data', 'pattern': 'Unknown'}
    
    yearly_stats = {}
    for ret in returns:
        fy = ret.get('fy', '')
        if fy:
            if fy not in yearly_stats:
                yearly_stats[fy] = {'total': 0, 'filed': 0}
            yearly_stats[fy]['total'] += 1
            if ret.get('dof'):
                yearly_stats[fy]['filed'] += 1
    
    rates = []
    for year in sorted(yearly_stats.keys()):
        rate = (yearly_stats[year]['filed'] / yearly_stats[year]['total']) * 100
        rates.append(rate)
    
    if len(rates) >= 2:
        recent_rate = sum(rates[-2:]) / 2
        earlier_rate = sum(rates[:-2]) / len(rates[:-2]) if len(rates) > 2 else rates[0]
        
        if recent_rate > earlier_rate + 10:
            trend = 'Improving'
        elif recent_rate < earlier_rate - 10:
            trend = 'Declining'
        else:
            trend = 'Stable'
    else:
        trend = 'Insufficient Data'
    
    return {
        'trend': trend,
        'yearly_stats': yearly_stats,
        'current_rate': rates[-1] if rates else 0
    }

def assess_business_health(data: Dict) -> Dict:
    """Assess overall business health"""
    returns = data.get('returns', [])
    compliance = data.get('compliance', {})
    
    health_score = 0
    factors = []
    
    # Active status (20 points)
    if data.get('sts', '').lower() == 'active':
        health_score += 20
        factors.append('Active registration status')
    else:
        factors.append('Non-active registration status (-20)')
    
    # Compliance score (40 points)
    comp_score = compliance.get('score', 0)
    health_score += (comp_score / 100) * 40
    factors.append(f'Compliance score: {comp_score}%')
    
    # Filing rate (25 points)
    if returns:
        filed_rate = len([r for r in returns if r.get('dof')]) / len(returns)
        health_score += filed_rate * 25
        factors.append(f'Filing rate: {filed_rate*100:.1f}%')
    
    # Recent activity (15 points)
    if returns:
        recent_returns = sorted(returns, key=lambda x: (x.get('fy', ''), x.get('taxp', '')), reverse=True)[:3]
        recent_filed = sum(1 for r in recent_returns if r.get('dof'))
        recent_rate = recent_filed / len(recent_returns) if recent_returns else 0
        health_score += recent_rate * 15
        factors.append(f'Recent activity rate: {recent_rate*100:.1f}%')
    
    # Determine grade
    if health_score >= 90:
        grade = 'Excellent'
        status = 'Very Healthy Business'
    elif health_score >= 75:
        grade = 'Good'
        status = 'Healthy Business'
    elif health_score >= 60:
        grade = 'Fair'
        status = 'Moderate Health'
    elif health_score >= 40:
        grade = 'Poor'
        status = 'Concerning Health'
    else:
        grade = 'Critical'
        status = 'Poor Business Health'
    
    return {
        'score': round(health_score, 1),
        'grade': grade,
        'status': status,
        'factors': factors
    }

def generate_recommendations(data: Dict, synopsis: Dict) -> List[Dict]:
    """Generate actionable recommendations"""
    recommendations = []
    returns = data.get('returns', [])
    compliance = data.get('compliance', {})
    risk_flags = synopsis.get('risk_assessment', {}).get('red_flags', [])
    
    score = compliance.get('score', 0)
    
    # Compliance improvement
    if score < 70:
        recommendations.append({
            'category': 'Compliance',
            'priority': 'High',
            'title': 'Improve Filing Compliance',
            'description': 'Your compliance score is below optimal. Focus on timely filing of all due returns.',
            'action': 'Set up calendar reminders for all due dates and consider automated filing systems.'
        })
    
    # Late filing reduction
    late_returns = compliance.get('late_returns', 0)
    total_filed = compliance.get('filed_returns', 0)
    if total_filed > 0 and (late_returns / total_filed) > 0.2:
        recommendations.append({
            'category': 'Process',
            'priority': 'Medium',
            'title': 'Reduce Late Filings',
            'description': f'{(late_returns/total_filed*100):.1f}% of your returns are filed late.',
            'action': 'Implement a filing calendar and consider hiring a tax professional.'
        })
    
    # Recent activity
    recent_activity = synopsis.get('operational_insights', {}).get('recent_activity', '')
    if 'inactive' in recent_activity.lower():
        recommendations.append({
            'category': 'Activity',
            'priority': 'High',
            'title': 'Resume Filing Activities',
            'description': 'No recent filing activity detected. This may lead to compliance issues.',
            'action': 'Review all pending returns and file immediately to avoid penalties.'
        })
    
    # Risk management
    if 'Low compliance score' in risk_flags:
        recommendations.append({
            'category': 'Risk Management',
            'priority': 'High',
            'title': 'Address Compliance Risks',
            'description': 'Multiple compliance risks detected.',
            'action': 'Conduct a comprehensive compliance audit and rectify all issues.'
        })
    
    # Excellence maintenance
    if score >= 90 and not risk_flags:
        recommendations.append({
            'category': 'Maintenance',
            'priority': 'Low',
            'title': 'Maintain Excellence',
            'description': 'Excellent compliance record! Keep up the good work.',
            'action': 'Continue current filing practices and monitor for any changes in regulations.'
        })
    
    return recommendations

def calculate_penalty_risk(returns: List[Dict], compliance: Dict) -> Dict:
    """Calculate potential penalty risk"""
    if not returns:
        return {'risk_amount': 0, 'explanation': 'No returns to assess'}
    
    late_returns = [r for r in returns if r.get('late')]
    pending_returns = [r for r in returns if not r.get('dof')]
    
    penalty_estimate = 0
    explanation = []
    
    # Calculate penalties for late returns
    for ret in late_returns:
        ret_type = ret.get('rtype') or ret.get('rtntype', '')
        if ret_type in ['GSTR1', 'GSTR3B']:
            penalty_estimate += min(5000, 100 * 30)  # Simplified calculation
            explanation.append(f"Late {ret_type} penalty: ₹{min(5000, 100 * 30)}")
    
    # Calculate penalties for non-filed returns
    for ret in pending_returns:
        ret_type = ret.get('rtype') or ret.get('rtntype', '')
        if ret_type in ['GSTR1', 'GSTR3B']:
            penalty_estimate += 5000
            explanation.append(f"Non-filed {ret_type} penalty: ₹5,000")
    
    return {
        'risk_amount': penalty_estimate,
        'explanation': explanation,
        'currency': 'INR'
    }

def generate_enhanced_synopsis(data: Dict) -> Dict:
    """Generate enhanced synopsis with all analytics"""
    synopsis = generate_synopsis(data)
    synopsis['filing_trends'] = generate_filing_trends(data.get('returns', []))
    synopsis['business_health'] = assess_business_health(data)
    synopsis['recommendations'] = generate_recommendations(data, synopsis)
    synopsis['penalty_risk'] = calculate_penalty_risk(data.get('returns', []), data.get('compliance', {}))
    return synopsis

# FastAPI App Setup
app = FastAPI(title="GST Compliance Platform")

# Setup directories
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory="templates")

# API Client Setup
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")
api_client = GSAPIClient(RAPIDAPI_KEY, RAPIDAPI_HOST)

# Routes
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request, "data": None})

@app.post("/", response_class=HTMLResponse)
async def post_index(request: Request, gstin: str = Form(...)):
    """Process GSTIN search"""
    # Validate GSTIN
    is_valid, validation_message = validate_gstin(gstin)
    if not is_valid:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": validation_message,
            "error_type": "validation"
        })
    
    gstin = gstin.strip().upper()
    
    try:
        # Fetch data from API
        raw_data = await api_client.fetch_gstin_data(gstin)
        
        # Process returns
        returns = mark_late_returns(raw_data.get('returns', []))
        raw_data['returns'] = returns
        
        # Calculate compliance
        compliance = calculate_compliance_score(raw_data)
        
        # Organize returns by year
        returns_by_year = organize_returns_by_year(returns)
        
        # Generate enhanced synopsis
        synopsis = generate_enhanced_synopsis({**raw_data, 'compliance': compliance})
        
        # Get AI-powered narrative (with web search)
        ai_narrative = await get_anthropic_synopsis({**raw_data, "compliance": compliance})
        synopsis['narrative'] = ai_narrative
        
        # Prepare enhanced data
        enhanced_data = {
            **raw_data,
            'compliance': compliance,
            'returns_by_year': returns_by_year,
            'returns': returns,
            'synopsis': synopsis
        }
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": enhanced_data,
            "gstin": gstin
        })
        
    except HTTPException as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": e.detail,
            "error_type": "api"
        })
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": f"An error occurred: {str(e)}",
            "error_type": "system"
        })

@app.post("/download/pdf")
async def download_pdf(request: Request, gstin: str = Form(...)):
    """Generate PDF report"""
    # Validate GSTIN
    is_valid, validation_message = validate_gstin(gstin)
    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)
    
    try:
        # Fetch and process data (same as above)
        raw_data = await api_client.fetch_gstin_data(gstin)
        returns = mark_late_returns(raw_data.get('returns', []))
        raw_data['returns'] = returns
        compliance = calculate_compliance_score(raw_data)
        returns_by_year = organize_returns_by_year(returns)
        
        # Generate synopsis with AI narrative
        synopsis = generate_enhanced_synopsis({**raw_data, 'compliance': compliance})
        ai_narrative = await get_anthropic_synopsis({**raw_data, "compliance": compliance})
        synopsis['narrative'] = ai_narrative
        
        enhanced_data = {
            **raw_data,
            'compliance': compliance,
            'returns_by_year': returns_by_year,
            'returns': returns,
            'synopsis': synopsis
        }
        
        # Generate PDF
        html_content = templates.get_template("pdf_template.html").render(
            request=request,
            data=enhanced_data,
            gstin=gstin,
            error=None
        )
        
        pdf_file = BytesIO()
        HTML(string=html_content, base_url=os.path.abspath(".")).write_pdf(pdf_file)
        pdf_file.seek(0)
        
        return StreamingResponse(
            pdf_file,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={gstin}_gst_dashboard.pdf"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/pdf")
async def download_pdf_get(request: Request, gstin: str):
    """Generate PDF report via GET request"""
    # Validate GSTIN
    is_valid, validation_message = validate_gstin(gstin)
    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)
    
    try:
        # Reuse the POST logic
        raw_data = await api_client.fetch_gstin_data(gstin)
        returns = mark_late_returns(raw_data.get('returns', []))
        raw_data['returns'] = returns
        compliance = calculate_compliance_score(raw_data)
        returns_by_year = organize_returns_by_year(returns)
        
        synopsis = generate_enhanced_synopsis({**raw_data, 'compliance': compliance})
        ai_narrative = await get_anthropic_synopsis({**raw_data, "compliance": compliance})
        synopsis['narrative'] = ai_narrative
        
        enhanced_data = {
            **raw_data,
            'compliance': compliance,
            'returns_by_year': returns_by_year,
            'returns': returns,
            'synopsis': synopsis
        }
        
        html_content = templates.get_template("pdf_template.html").render(
            request=request,
            data=enhanced_data,
            gstin=gstin,
            error=None
        )
        
        pdf_file = BytesIO()
        HTML(string=html_content, base_url=os.path.abspath(".")).write_pdf(pdf_file)
        pdf_file.seek(0)
        
        return StreamingResponse(
            pdf_file,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={gstin}_gst_dashboard.pdf"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)