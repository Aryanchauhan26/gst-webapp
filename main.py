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

# Import WeasyPrint for HTML-to-PDF
from weasyprint import HTML

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
    enhanced_data = {
        **raw_data,
        'compliance': compliance,
        'returns_by_year': returns_by_year,
        'returns': returns
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
    enhanced_data = {
        **raw_data,
        'compliance': compliance,
        'returns_by_year': returns_by_year,
        'returns': returns
    }
    # Pass 'request' so 'url_for' works in the template
    html_content = templates.get_template("pdf_template.html").render(
        request=request,
        data=enhanced_data,
        gstin=gstin,
        error=None
    )
    pdf_file = BytesIO()
    HTML(string=html_content, base_url="").write_pdf(pdf_file)
    pdf_file.seek(0)
    return StreamingResponse(pdf_file, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename={gstin}_gst_dashboard.pdf"
    })