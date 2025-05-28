from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import httpx
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Tuple
from collections import defaultdict, deque
import hashlib
import os
from pathlib import Path
import re

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

# --- Logging, Error Tracker, Rate Limiter, etc omitted for brevity. Use your existing code for those. ---

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
                        late_count += 1
            except Exception:
                pass
        if dof:
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

# --- FastAPI app setup ---
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
    compliance = calculate_enhanced_compliance_score(raw_data)
    returns_by_year = organize_returns_by_year(raw_data.get('returns', []))
    enhanced_data = {
        **raw_data,
        'compliance': compliance,
        'returns_by_year': returns_by_year,
        'returns': raw_data.get('returns', [])
    }
    return templates.TemplateResponse("index.html", {
        "request": request,
        "data": enhanced_data,
        "gstin": gstin
    })

@app.post("/download/pdf")
async def download_pdf(gstin: str = Form(...)):
    is_valid, validation_message = validate_gstin(gstin)
    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)
    raw_data = await api_client.fetch_gstin_data(gstin)
    compliance = calculate_enhanced_compliance_score(raw_data)
    returns_by_year = organize_returns_by_year(raw_data.get('returns', []))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="TitleStyle",
        parent=styles["Title"],
        alignment=1,
        fontSize=20,
        textColor=colors.white,
        backColor=colors.HexColor("#4169E1"),
        spaceAfter=18,
        spaceBefore=0,
        leading=24,
        borderPadding=(10,10,10,10)
    )
    section_header = ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.white,
        backColor=colors.HexColor("#4682B4"),
        spaceAfter=10,
        leftIndent=0,
        leading=18
    )
    normal = styles["Normal"]
    bold = ParagraphStyle(name="Bold", parent=normal, fontName="Helvetica-Bold")
    elements = []

    # Colored title bar
    elements.append(Paragraph("GST Status Report", title_style))
    elements.append(Spacer(1, 10))

    # Company info
    elements.append(Paragraph("Company Information", section_header))
    company_table = Table([
        ["Legal Name:", raw_data.get('lgnm', '')],
        ["Trade Name:", raw_data.get('tradeName', '')],
        ["GSTIN:", raw_data.get('gstin', '')],
        ["Status:", raw_data.get('sts', '')],
        ["Registration Date:", raw_data.get('rgdt', '')],
        ["Company Type:", raw_data.get('ctb', '')],
        ["Jurisdiction:", raw_data.get('ctj', '')],
        ["Registered Address:", raw_data.get('adr', '')],
        ["e-Invoicing Applicable:", "Yes" if raw_data.get("mandatedeInvoice") == "Yes" or raw_data.get("einvoiceStatus") == "Yes" else "No"],
    ], hAlign="LEFT", colWidths=[5*cm, 10*cm])
    company_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#E6E6FA")),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor("#4169E1")),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    elements.append(company_table)
    elements.append(Spacer(1, 18))

    # Compliance summary
    elements.append(Paragraph("Compliance Summary", section_header))
    compliance_grid = Table([
        ["Compliance Score", f"{compliance['score']}%"],
        ["Grade", compliance['grade']],
        ["Status", compliance['status']],
        ["Total Returns", compliance['total_returns']],
        ["Filed Returns", compliance['filed_returns']],
        ["Late Returns", compliance['late_returns']],
        ["Pending Returns", compliance['pending_returns']],
    ], hAlign="LEFT", colWidths=[6*cm, 4*cm])
    compliance_grid.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#F0F8FF")),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor("#2F4F4F")),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor("#2F4F4F")),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(compliance_grid)
    elements.append(Spacer(1, 18))

    # Returns by year
    elements.append(Paragraph("GST Return Filing History", section_header))
    for fy, retlist in returns_by_year.items():
        elements.append(Paragraph(f"Financial Year: {fy}", bold))
        ret_data = [["Return Type", "Tax Period", "Filing Date", "Status"]]
        for idx, ret in enumerate(retlist):
            filed = bool(ret.get('dof'))
            status_text = "Filed" if filed else "Pending"
            ret_data.append([
                ret.get("rtntype", ""),
                ret.get("taxp", ""),
                ret.get("dof", "Pending"),
                status_text
            ])
        table = Table(ret_data, colWidths=[3*cm, 4*cm, 4*cm, 3*cm], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#B0C4DE")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#333333")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 11),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#E0FFFF"), colors.white]),
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 10))
    doc.build(elements)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment;filename={gstin}_gst_report.pdf"
    })