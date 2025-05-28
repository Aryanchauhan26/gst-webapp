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
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

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
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        # Title
        story.append(Paragraph("GST RETURN STATUS REPORT", title_style))
        story.append(Spacer(1, 20))
        
        # Generated date
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Company Information Section
        story.append(Paragraph("COMPANY INFORMATION", heading_style))
        
        company_data = [
            ['Legal Name:', data.get('lgnm', 'N/A')],
            ['Trade Name:', data.get('tradeName', 'N/A')],
            ['GSTIN:', data.get('gstin', 'N/A')],
            ['Status:', data.get('sts', 'N/A')],
            ['Registration Date:', data.get('rgdt', 'N/A')],
            ['Company Type:', data.get('ctb', 'N/A')],
            ['Address:', data.get('adr', 'N/A')[:100] + '...' if data.get('adr') and len(data.get('adr', '')) > 100 else data.get('adr', 'N/A')]
        ]
        
        company_table = Table(company_data, colWidths=[2*inch, 4*inch])
        company_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(company_table)
        story.append(Spacer(1, 20))
        
        # Compliance Summary
        compliance = calculate_compliance_score(data)
        story.append(Paragraph("COMPLIANCE SUMMARY", heading_style))
        
        compliance_data = [
            ['Compliance Score:', f"{compliance['score']}%"],
            ['Grade:', compliance['grade']],
            ['Status:', compliance['status']],
            ['Total Returns:', str(compliance['total_returns'])],
            ['Filed Returns:', str(compliance['filed_returns'])]
        ]
        
        compliance_table = Table(compliance_data, colWidths=[2*inch, 4*inch])
        compliance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (1, 0), (1, -1), colors.lightcyan),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(compliance_table)
        story.append(Spacer(1, 20))
        
        # Filing History
        story.append(Paragraph("FILING HISTORY", heading_style))
        
        if data.get('returns'):
            filing_data = [['Return Type', 'Tax Period', 'Financial Year', 'Status', 'Date Filed']]
            
            for ret in data['returns'][:20]:  # Limit to first 20 returns to avoid overflow
                if ret.get('rtntype') and ret.get('taxp'):
                    filed_status = "Filed" if ret.get('dof') else "Not Filed"
                    filing_data.append([
                        ret.get('rtntype', 'N/A'),
                        ret.get('taxp', 'N/A'),
                        ret.get('fy', 'N/A'),
                        filed_status,
                        ret.get('dof', 'N/A')
                    ])
            
            filing_table = Table(filing_data, colWidths=[1.2*inch, 1.2*inch, 1*inch, 1*inch, 1.6*inch])
            filing_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            story.append(filing_table)
        else:
            story.append(Paragraph("No filing history available.", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=GST_Report_{gstin}.pdf"}
        )
        
    except Exception as e:
        return Response(content=f"Error generating PDF report: {str(e)}", status_code=500)

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
            company_df = pd.DataFrame(company_info)
            company_df.to_excel(writer, sheet_name='Company Info', index=False)
            
            # Returns History Sheet
            if data.get('returns'):
                returns_df = pd.DataFrame(data['returns'])
                returns_df.to_excel(writer, sheet_name='Filing History', index=False)
            else:
                # Create empty sheet with headers
                empty_df = pd.DataFrame(columns=['rtntype', 'taxp', 'fy', 'dof', 'status'])
                empty_df.to_excel(writer, sheet_name='Filing History', index=False)
            
            # Compliance Summary Sheet
            compliance = calculate_compliance_score(data)
            compliance_info = {
                'Metric': ['Compliance Score (%)', 'Grade', 'Status', 'Total Returns', 'Filed Returns'],
                'Value': [compliance['score'], compliance['grade'], compliance['status'], 
                         compliance['total_returns'], compliance['filed_returns']]
            }
            compliance_df = pd.DataFrame(compliance_info)
            compliance_df.to_excel(writer, sheet_name='Compliance Summary', index=False)
            
            # Format the Excel file
            workbook = writer.book
            
            # Format Company Info sheet
            company_sheet = writer.sheets['Company Info']
            for column in company_sheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                company_sheet.column_dimensions[column_letter].width = adjusted_width
            
            # Format Filing History sheet if it exists
            if 'Filing History' in writer.sheets:
                filing_sheet = writer.sheets['Filing History']
                for column in filing_sheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 30)
                    filing_sheet.column_dimensions[column_letter].width = adjusted_width
        
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
