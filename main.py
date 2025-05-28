from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import requests
import json
from datetime import datetime
import pandas as pd
from io import BytesIO
import urllib.parse

app = FastAPI()

# Mount static folder for CSS
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

RAPIDAPI_KEY = "08cbf9855dmsh5c8d8660645305cp1a8713jsn17eca3b207a5"
RAPIDAPI_HOST = "gst-return-status.p.rapidapi.com"

def calculate_compliance_score(data):
    """Calculate compliance score based on filing history"""
    if not data.get('returns'):
        return {"score": 0, "grade": "N/A", "status": "No filing history"}
    
    total_returns = len(data['returns'])
    filed_returns = len([r for r in data['returns'] if r.get('dof')])
    
    if total_returns == 0:
        compliance_rate = 0
    else:
        compliance_rate = (filed_returns / total_returns) * 100
    
    if compliance_rate >= 90:
        grade = "A+"
        status = "Excellent"
    elif compliance_rate >= 80:
        grade = "A"
        status = "Good"
    elif compliance_rate >= 70:
        grade = "B"
        status = "Average"
    elif compliance_rate >= 60:
        grade = "C"
        status = "Below Average"
    else:
        grade = "D"
        status = "Poor"
    
    return {
        "score": round(compliance_rate, 1),
        "grade": grade,
        "status": status,
        "total_returns": total_returns,
        "filed_returns": filed_returns
    }

def organize_returns_by_year(returns):
    """Organize returns by financial year"""
    organized = {}
    if not returns:
        return organized
    
    for ret in returns:
        if ret.get('fy'):
            fy = ret['fy']
            if fy not in organized:
                organized[fy] = []
            organized[fy].append(ret)
    
    # Sort by year (descending)
    return dict(sorted(organized.items(), reverse=True))

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "data": None})

@app.post("/", response_class=HTMLResponse)
async def post_index(request: Request, gstin: str = Form(...)):
    url = f"https://gst-return-status.p.rapidapi.com/free/gstin/{gstin}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        json_data = response.json()
        data = json_data.get("data", {})
        
        # Calculate compliance score
        compliance = calculate_compliance_score(data)
        
        # Organize returns by year
        returns_by_year = organize_returns_by_year(data.get('returns', []))
        
        # Add processed data
        data['compliance'] = compliance
        data['returns_by_year'] = returns_by_year
        
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "data": data,
            "gstin": gstin
        })
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": str(e)
        })

@app.post("/download/pdf")
async def download_pdf(gstin: str = Form(...)):
    """Generate and download PDF report"""
    # For this example, I'll create a simple text-based report
    # In production, you'd want to use a proper PDF library like ReportLab
    
    url = f"https://gst-return-status.p.rapidapi.com/free/gstin/{gstin}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        json_data = response.json()
        data = json_data.get("data", {})
        
        # Create a simple text report
        report = f"""
GST RETURN STATUS REPORT
========================
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

COMPANY INFORMATION
------------------
Legal Name: {data.get('lgnm', 'N/A')}
Trade Name: {data.get('tradeName', 'N/A')}
GSTIN: {data.get('gstin', 'N/A')}
Status: {data.get('sts', 'N/A')}
Registration Date: {data.get('rgdt', 'N/A')}
Company Type: {data.get('ctb', 'N/A')}
Address: {data.get('adr', 'N/A')}

COMPLIANCE SUMMARY
-----------------
"""
        
        compliance = calculate_compliance_score(data)
        report += f"""
Compliance Score: {compliance['score']}%
Grade: {compliance['grade']}
Status: {compliance['status']}
Total Returns: {compliance['total_returns']}
Filed Returns: {compliance['filed_returns']}

FILING HISTORY
--------------
"""
        
        if data.get('returns'):
            for ret in data['returns']:
                if ret.get('rtntype') and ret.get('taxp'):
                    filed_status = "✓ Filed" if ret.get('dof') else "✗ Not Filed"
                    report += f"{ret['rtntype']} - {ret['taxp']} {ret.get('fy', '')} - {filed_status}\n"
        else:
            report += "No filing history available.\n"
        
        # Return as downloadable text file (you can enhance this to actual PDF)
        return Response(
            content=report,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=GST_Report_{gstin}.txt"}
        )
        
    except Exception as e:
        return Response(content=f"Error generating report: {str(e)}", status_code=500)

@app.post("/download/excel")
async def download_excel(gstin: str = Form(...)):
    """Generate and download Excel report"""
    
    url = f"https://gst-return-status.p.rapidapi.com/free/gstin/{gstin}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        json_data = response.json()
        data = json_data.get("data", {})
        
        # Create Excel file with multiple sheets
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Company Info Sheet
            company_info = {
                'Field': ['Legal Name', 'Trade Name', 'GSTIN', 'Status', 'Registration Date', 'Company Type', 'Address'],
                'Value': [
                    data.get('lgnm', 'N/A'),
                    data.get('tradeName', 'N/A'),
                    data.get('gstin', 'N/A'),
                    data.get('sts', 'N/A'),
                    data.get('rgdt', 'N/A'),
                    data.get('ctb', 'N/A'),
                    data.get('adr', 'N/A')
                ]
            }
            pd.DataFrame(company_info).to_excel(writer, sheet_name='Company Info', index=False)
            
            # Returns History Sheet
            if data.get('returns'):
                returns_df = pd.DataFrame(data['returns'])
                returns_df.to_excel(writer, sheet_name='Filing History', index=False)
            
            # Compliance Summary Sheet
            compliance = calculate_compliance_score(data)
            compliance_info = {
                'Metric': ['Compliance Score (%)', 'Grade', 'Status', 'Total Returns', 'Filed Returns'],
                'Value': [compliance['score'], compliance['grade'], compliance['status'], 
                         compliance['total_returns'], compliance['filed_returns']]
            }
            pd.DataFrame(compliance_info).to_excel(writer, sheet_name='Compliance Summary', index=False)
        
        output.seek(0)
        
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=GST_Report_{gstin}.xlsx"}
        )
        
    except Exception as e:
        return Response(content=f"Error generating Excel report: {str(e)}", status_code=500)

@app.get("/whatsapp/{gstin}")
async def share_whatsapp(gstin: str):
    """Generate WhatsApp share link"""
    
    url = f"https://gst-return-status.p.rapidapi.com/free/gstin/{gstin}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        json_data = response.json()
        data = json_data.get("data", {})
        
        compliance = calculate_compliance_score(data)
        
        # Create WhatsApp message
        message = f"""*GST Status Report*
📊 *Company:* {data.get('lgnm', 'N/A')}
🏢 *GSTIN:* {data.get('gstin', 'N/A')}
✅ *Status:* {data.get('sts', 'N/A')}
📈 *Compliance Score:* {compliance['score']}% ({compliance['grade']})
📅 *Registration Date:* {data.get('rgdt', 'N/A')}

Generated via GST Lookup Tool"""
        
        # URL encode the message
        encoded_message = urllib.parse.quote(message)
        whatsapp_url = f"https://wa.me/?text={encoded_message}"
        
        return {"whatsapp_url": whatsapp_url}
        
    except Exception as e:
        return {"error": str(e)}
