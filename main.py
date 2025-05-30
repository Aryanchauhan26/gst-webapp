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
from gemini_ai import get_gemini_synopsis

def validate_gstin(gstin: str) -> Tuple[bool, str]:
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
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key
        self.host = host
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host,
            "User-Agent": "GST-Compliance-Platform/2.0"
        }
    async def fetch_gstin_data(self, gstin: str, max_retries: int = 3) -> Dict:
        url = f"https://{self.host}/free/gstin/{gstin}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        if not data.get("success", False):
            raise HTTPException(status_code=400, detail=f"API Error: {data.get('message', 'Unknown error')}")
        return data.get("data", {})

def mark_late_returns(returns):
    for ret in returns:
        ret['late'] = False
        dof = ret.get("dof")
        fy = ret.get("fy")
        month_str = ret.get("taxp")
        rtntype = ret.get("rtntype", "")
        if fy and month_str and dof:
            try:
                if "-" in fy:
                    year = int(fy.split("-")[0])
                else:
                    year = int(fy)
                month_map = {m: i for i, m in enumerate(
                    ["April","May","June","July","August","September","October","November","December","January","February","March"], start=4)}
                month = month_map.get(month_str, None)
                if month is not None:
                    if month < 4:
                        year += 1
                    due_day = 11 if rtntype.upper() == "GSTR1" else 20
                    due_date = datetime(year, month, due_day)
                    filed_date = datetime.strptime(dof, "%d/%m/%Y")
                    if filed_date > due_date:
                        ret['late'] = True
            except Exception:
                pass
    return returns

def calculate_enhanced_compliance_score(data: Dict) -> Dict:
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
    filed_count, late_count = 0, 0
    total_count = len(returns)
    for ret in returns:
        if ret.get('late'):
            late_count += 1
        if ret.get("dof"):
            filed_count += 1
    on_time_count = filed_count - late_count
    score = round(((on_time_count + 0.5 * late_count) / total_count) * 100, 1)
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
    returns_by_year = defaultdict(list)
    for ret in returns:
        fy = ret.get('fy')
        if fy:
            returns_by_year[fy].append(ret)
    sorted_years = dict(sorted(returns_by_year.items(), reverse=True))
    return sorted_years

def generate_filing_trends(returns: List[Dict]) -> Dict:
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
    returns = data.get('returns', [])
    compliance = data.get('compliance', {})
    health_score = 0
    factors = []
    if data.get('sts', '').lower() == 'active':
        health_score += 20
        factors.append('Active registration status')
    else:
        factors.append('Non-active registration status (-20)')
    comp_score = compliance.get('score', 0)
    health_score += (comp_score / 100) * 40
    factors.append(f'Compliance score: {comp_score}%')
    if returns:
        filed_rate = len([r for r in returns if r.get('dof')]) / len(returns)
        health_score += filed_rate * 25
        factors.append(f'Filing rate: {filed_rate*100:.1f}%')
    if returns:
        recent_returns = sorted(returns, key=lambda x: (x.get('fy', ''), x.get('taxp', '')), reverse=True)[:3]
        recent_filed = sum(1 for r in recent_returns if r.get('dof'))
        recent_rate = recent_filed / len(recent_returns) if recent_returns else 0
        health_score += recent_rate * 15
        factors.append(f'Recent activity rate: {recent_rate*100:.1f}%')
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
    recommendations = []
    returns = data.get('returns', [])
    compliance = data.get('compliance', {})
    risk_flags = synopsis.get('risk_assessment', {}).get('red_flags', [])
    score = compliance.get('score', 0)
    if score < 70:
        recommendations.append({
            'category': 'Compliance',
            'priority': 'High',
            'title': 'Improve Filing Compliance',
            'description': 'Your compliance score is below optimal. Focus on timely filing of all due returns.',
            'action': 'Set up calendar reminders for all due dates and consider automated filing systems.'
        })
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
    recent_activity = synopsis.get('operational_insights', {}).get('recent_activity', '')
    if 'inactive' in recent_activity.lower():
        recommendations.append({
            'category': 'Activity',
            'priority': 'High',
            'title': 'Resume Filing Activities',
            'description': 'No recent filing activity detected. This may lead to compliance issues.',
            'action': 'Review all pending returns and file immediately to avoid penalties.'
        })
    if 'Low compliance score' in risk_flags:
        recommendations.append({
            'category': 'Risk Management',
            'priority': 'High',
            'title': 'Address Compliance Risks',
            'description': 'Multiple compliance risks detected.',
            'action': 'Conduct a comprehensive compliance audit and rectify all issues.'
        })
    if score >= 90 and not risk_flags:
        recommendations.append({
            'category': 'Maintenance',
            'priority': 'Low',
            'title': 'Maintain Excellence',
            'description': 'Excellent compliance record! Keep up the good work.',
            'action': 'Continue current filing practices and monitor for any changes in regulations.'
        })
    return recommendations

def calculate_penalty_risk_amount(returns: List[Dict], compliance: Dict) -> Dict:
    if not returns:
        return {'risk_amount': 0, 'explanation': 'No returns to assess'}
    late_returns = [r for r in returns if r.get('late')]
    pending_returns = [r for r in returns if not r.get('dof')]
    penalty_estimate = 0
    explanation = []
    for ret in late_returns:
        ret_type = ret.get('rtype') or ret.get('rtntype', '')
        if ret_type in ['GSTR1', 'GSTR3B']:
            penalty_estimate += min(5000, 100 * 30)
            explanation.append(f"Late {ret_type} penalty: ₹{min(5000, 100 * 30)}")
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

def generate_company_synopsis(data: Dict) -> Dict:
    synopsis = {
        'business_profile': {},
        'operational_insights': {},
        'compliance_summary': {},
        'risk_assessment': {},
        'key_metrics': {}
    }
    company_name = data.get('lgnm', 'Unknown Company')
    trade_name = data.get('tradeName', '')
    registration_date = data.get('rgdt', '')
    company_type = data.get('ctb', '')
    status = data.get('sts', '')
    gstin = data.get('gstin', '')
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
    state_map = {
        '01': 'Jammu & Kashmir', '02': 'Himachal Pradesh', '03': 'Punjab', '04': 'Chandigarh',
        '05': 'Uttarakhand', '06': 'Haryana', '07': 'Delhi', '08': 'Rajasthan',
        '09': 'Uttar Pradesh', '10': 'Bihar', '11': 'Sikkim', '12': 'Arunachal Pradesh',
        '13': 'Nagaland', '14': 'Manipur', '15': 'Mizoram', '16': 'Tripura',
        '17': 'Meghalaya', '18': 'Assam', '19': 'West Bengal', '20': 'Jharkhand',
        '21': 'Odisha', '22': 'Chhattisgarh', '23': 'Madhya Pradesh', '24': 'Gujarat',
        '25': 'Daman & Diu', '26': 'Dadra & Nagar Haveli', '27': 'Maharashtra',
        '28': 'Andhra Pradesh', '29': 'Karnataka', '30': 'Goa', '31': 'Lakshadweep',
        '32': 'Kerala', '33': 'Tamil Nadu', '34': 'Puducherry', '35': 'Andaman & Nicobar',
        '36': 'Telangana', '37': 'Andhra Pradesh'
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
    synopsis['key_metrics'] = {
        'business_age_years': int(business_age.split()[0]) if business_age != "Unknown" and business_age.split()[0].isdigit() else 0,
        'filing_percentage': f"{returns_filed / total_returns_due * 100:.1f}%" if total_returns_due else "0%",
        'compliance_grade': grade,
        'total_late_returns': late_returns,
        'active_status': status == 'Active'
    }
    narrative = f"{synopsis['business_profile']['display_name']} is a {synopsis['business_profile']['entity_type']} "
    narrative += f"operating for {business_age} in {state_name}. "
    narrative += f"The company is classified as a '{filing_consistency}' with an overall compliance grade of '{grade}'. "
    if recent_activity == 'Active and compliant':
        narrative += "Recent filing activity shows good compliance discipline."
    elif recent_activity == 'Inactive filing':
        narrative += "Recent filing activity shows concerning gaps in compliance."
    else:
        narrative += "Shows mixed compliance patterns in recent filings."
    synopsis['narrative'] = narrative
    return synopsis

def generate_enhanced_synopsis(data: Dict) -> Dict:
    synopsis = generate_company_synopsis(data)
    synopsis['filing_trends'] = generate_filing_trends(data.get('returns', []))
    synopsis['business_health'] = assess_business_health(data)
    synopsis['recommendations'] = generate_recommendations(data, synopsis)
    synopsis['penalty_risk'] = calculate_penalty_risk_amount(data.get('returns', []), data.get('compliance', {}))
    return synopsis

app = FastAPI(title="GST Compliance Platform")
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory="templates")

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")
api_client = GSAPIClient(RAPIDAPI_KEY, RAPIDAPI_HOST)

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "data": None})

@app.post("/", response_class=HTMLResponse)
async def post_index(request: Request, gstin: str = Form(...)):
    is_valid, validation_message = validate_gstin(gstin)
    if not is_valid:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": validation_message,
            "error_type": "validation"
        })
    gstin = gstin.strip().upper()
    raw_data = await api_client.fetch_gstin_data(gstin)
    returns = mark_late_returns(raw_data.get('returns', []))
    raw_data['returns'] = returns
    compliance = calculate_enhanced_compliance_score(raw_data)
    returns_by_year = organize_returns_by_year(returns)
    # Fetch Gemini synopsis
    ai_narrative = await run_in_threadpool(get_gemini_synopsis, {**raw_data, "compliance": compliance})
    synopsis = generate_enhanced_synopsis({**raw_data, 'compliance': compliance})
    synopsis['narrative'] = ai_narrative
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

@app.post("/download/pdf")
async def download_pdf(request: Request, gstin: str = Form(...)):
    is_valid, validation_message = validate_gstin(gstin)
    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)
    raw_data = await api_client.fetch_gstin_data(gstin)
    returns = mark_late_returns(raw_data.get('returns', []))
    raw_data['returns'] = returns
    compliance = calculate_enhanced_compliance_score(raw_data)
    returns_by_year = organize_returns_by_year(returns)
    # Fetch Gemini synopsis
    ai_narrative = await run_in_threadpool(get_gemini_synopsis, {**raw_data, "compliance": compliance})
    synopsis = generate_enhanced_synopsis({**raw_data, 'compliance': compliance})
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
    return StreamingResponse(pdf_file, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename={gstin}_gst_dashboard.pdf"
    })