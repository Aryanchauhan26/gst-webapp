from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
from datetime import datetime

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

RAPIDAPI_KEY = "08cbf9855dmsh5c8d8660645305cp1a8713jsn17eca3b207a5"
API_HOST = "gst-return-filing-data.p.rapidapi.com"

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "data": None, "error": None})

@app.post("/", response_class=HTMLResponse)
def fetch_gst_returns(request: Request, gstin: str = Form(...)):
    gstin = gstin.strip().upper()
    if len(gstin) != 15 or not gstin.isalnum():
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "❌ Invalid GST Number. Please enter a valid 15-character GSTIN.",
            "data": None
        })

    current_year = datetime.now().year
    financial_year = f"{current_year - 1}-{str(current_year)[-2:]}"  # Example: 2024-25

    url = f"https://{API_HOST}/v1/gst-returns/{gstin}/{financial_year}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": API_HOST
    }

    try:
        response = requests.get(url, headers=headers)
        result = response.json()

        if not result.get("data"):
            return templates.TemplateResponse("index.html", {
                "request": request,
                "error": result.get("message", "GST return data not found."),
                "data": None
            })

        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": {
                "gstin": gstin,
                "financialYear": financial_year,
                "returns": result["data"]
            },
            "error": None
        })

    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": f"API call failed: {str(e)}",
            "data": None
        })

@app.get("/rate", response_class=HTMLResponse)
def rate_company(request: Request, gstin: str):
    current_year = datetime.now().year
    financial_year = f"{current_year - 1}-{str(current_year)[-2:]}"
    url = f"https://{API_HOST}/v1/gst-returns/{gstin}/{financial_year}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": API_HOST
    }

    try:
        response = requests.get(url, headers=headers)
        result = response.json()
        filings = result.get("data", [])

        if not filings:
            return templates.TemplateResponse("rate.html", {
                "request": request,
                "error": "No filing data found for rating.",
                "rating": None
            })

        filed_returns = sum(1 for f in filings if f.get("filingStatus", "").lower() == "filed")
        total_returns = len(filings)
        score = (filed_returns / total_returns) * 5 if total_returns else 0

        return templates.TemplateResponse("rate.html", {
            "request": request,
            "rating": round(score, 1),
            "filed": filed_returns,
            "total": total_returns,
            "financialYear": financial_year,
            "error": None
        })

    except Exception as e:
        return templates.TemplateResponse("rate.html", {
            "request": request,
            "error": f"Rating fetch failed: {str(e)}",
            "rating": None
        })
