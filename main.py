from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests

app = FastAPI()

# ────────────────────────────
# Static files & templates
# ────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ────────────────────────────
# RapidAPI credentials
# ────────────────────────────
RAPIDAPI_KEY  = "08cbf9855dmsh5c8d8660645305cp1a8713jsn17eca3b207a5"
RAPIDAPI_HOST = "gst-insights-api.p.rapidapi.com"

# ────────────────────────────
# Routes
# ────────────────────────────
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
        data = response.json()

        if not data.get("data"):
            return templates.TemplateResponse("index.html", {
                "request": request,
                "error": data.get("message", "GSTIN not found or inactive."),
                "data": None
            })

        gst_data = data["data"]

        principal = gst_data.get("principalAddress", {}).get("address", {})
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
                "gstin": gst_data.get("gstNumber"),
                "legalName": gst_data.get("legalName"),
                "tradeName": gst_data.get("tradeName"),
                "status": gst_data.get("status"),
                "registrationDate": gst_data.get("registration_date"),
                "cancellationDate": gst_data.get("cancelledDate"),
                "stateJurisdiction": gst_data.get("stateJurisdiction"),
                "centreJurisdiction": gst_data.get("centerJurisdiction"),
                "businessConstitution": gst_data.get("constitutionOfBusiness"),
                "type": gst_data.get("taxType"),
                "eInvoiceStatus": gst_data.get("eInvoiceStatus"),
                "principalAddress": principal_address,
                "additionalAddresses": gst_data.get("additionalAddress", []),
                "businessActivityNature": gst_data.get("natureOfBusinessActivity", [])
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
        data = response.json()

        if not data.get("data"):
            return templates.TemplateResponse("rate.html", {
                "request": request,
                "error": "Could not retrieve data for rating.",
                "rating": None
            })

        gst_data = data["data"]

        score = 0
        if gst_data.get("status") == "Active":
            score += 2
        if gst_data.get("eInvoiceStatus") == "Enabled":
            score += 2
        if gst_data.get("natureOfBusinessActivity"):
            score += 1
        if len(gst_data.get("additionalAddress", [])) > 0:
            score += 1
        if not gst_data.get("cancelledDate"):
            score += 2

        rating_out_of_5 = round(score / 8 * 5, 1)

        return templates.TemplateResponse("rate.html", {
            "request": request,
            "rating": rating_out_of_5,
            "details": {
                "status": gst_data.get("status"),
                "eInvoiceStatus": gst_data.get("eInvoiceStatus"),
                "businessActivity": gst_data.get("natureOfBusinessActivity", []),
                "additionalAddresses": len(gst_data.get("additionalAddress", [])),
                "cancelledDate": gst_data.get("cancelledDate")
            },
            "error": None
        })

    except Exception as e:
        return templates.TemplateResponse("rate.html", {
            "request": request,
            "error": f"Error fetching data: {str(e)}",
            "rating": None
        })

