from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

RAPIDAPI_KEY  = "08cbf9855dmsh5c8d8660645305cp1a8713jsn17eca3b207a5"
RAPIDAPI_HOST = "gst-insights-api.p.rapidapi.com"

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "data": None, "error": None})

@app.post("/", response_class=HTMLResponse)
def fetch_gst_data(request: Request, gstin: str = Form(...)):
    gstin = gstin.strip().upper()

    if len(gstin) != 15 or not gstin.isalnum():
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "❌ Invalid GST Number. Please enter a valid 15-character GSTIN in UPPERCASE.",
            "data": None
        })

    url = f"https://{RAPIDAPI_HOST}/getGSTDetailsUsingGST/{gstin}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

    try:
        response = requests.get(url, headers=headers)
        result = response.json()

        if not result.get("data"):
            return templates.TemplateResponse("index.html", {
                "request": request,
                "error": result.get("message", "GSTIN not found or inactive."),
                "data": None
            })

        data = result["data"]

        principal = data.get("principalAddress", {}).get("address", {})
        principal_address = ", ".join(filter(None, [
            principal.get("buildingNumber"),
            principal.get("buildingName"),
            principal.get("street"),
            principal.get("location"),
            principal.get("district"),
            principal.get("stateCode"),
            principal.get("pincode")
        ]))

        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": {
                "gstin": data.get("gstNumber"),
                "legalName": data.get("legalName"),
                "tradeName": data.get("tradeName"),
                "status": data.get("status"),
                "registrationDate": data.get("registration_date"),
                "cancellationDate": data.get("cancelledDate"),
                "stateJurisdiction": data.get("stateJurisdiction"),
                "centreJurisdiction": data.get("centerJurisdiction"),
                "businessConstitution": data.get("constitutionOfBusiness"),
                "type": data.get("taxType"),
                "eInvoiceStatus": data.get("eInvoiceStatus"),
                "principalAddress": principal_address,
                "additionalAddresses": data.get("additionalAddress", []),
                "businessActivityNature": data.get("natureOfBusinessActivity", [])
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
    url = f"https://{RAPIDAPI_HOST}/getGSTDetailsUsingGST/{gstin}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

    try:
        response = requests.get(url, headers=headers)
        result = response.json()

        if not result.get("data"):
            return templates.TemplateResponse("rate.html", {
                "request": request,
                "error": "Could not retrieve data for rating.",
                "rating": None
            })

        data = result["data"]

        score = 0
        if data.get("status") == "Active":
            score += 2
        if data.get("eInvoiceStatus") == "Enabled":
            score += 2
        if data.get("natureOfBusinessActivity"):
            score += 1
        if len(data.get("additionalAddress", [])) > 0:
            score += 1
        if not data.get("cancelledDate"):
            score += 2

        rating_out_of_5 = round(score / 8 * 5, 1)

        return templates.TemplateResponse("rate.html", {
            "request": request,
            "rating": rating_out_of_5,
            "details": {
                "status": data.get("status"),
                "eInvoiceStatus": data.get("eInvoiceStatus"),
                "businessActivity": data.get("natureOfBusinessActivity", []),
                "additionalAddresses": len(data.get("additionalAddress", [])),
                "cancelledDate": data.get("cancelledDate")
            },
            "error": None
        })

    except Exception as e:
        return templates.TemplateResponse("rate.html", {
            "request": request,
            "error": f"Error fetching data: {str(e)}",
            "rating": None
        })
