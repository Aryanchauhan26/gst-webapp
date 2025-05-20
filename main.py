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
    """Render empty form on GET."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "data": None, "error": None}
    )

@app.post("/", response_class=HTMLResponse)
def fetch_gst_data(request: Request, gstin: str = Form(...)):
    """Fetch GST info for a given GSTIN and render result."""
    url = f"https://{RAPIDAPI_HOST}/getGSTDetailsUsingGST/{gstin}"
    headers = {
        "X-RapidAPI-Key":  RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        print("FULL API Response:", data)          # <-- helpful for future debugging

        # Handle API-level errors
        if not data.get("success"):
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "error": data.get("message", "Invalid GSTIN or API error."),
                    "data": None,
                },
            )

        gst_data = data["data"]

        # ---------- Format address ----------
        addr_obj = (
            gst_data.get("principalAddress", {})
            .get("address", {})
        )
        formatted_address = ", ".join(
            filter(
                None,
                [
                    addr_obj.get("buildingNumber"),
                    addr_obj.get("street"),
                    addr_obj.get("location"),
                    addr_obj.get("district"),
                    addr_obj.get("stateCode"),
                    addr_obj.get("pincode"),
                ],
            )
        )

        # ---------- Render template ----------
        # Format principal address
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

 return templates.TemplateResponse(
            "index.html",
            {
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
                
                "error": None,
            },
        )

    except Exception as e:
        print("Exception:", e)
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": "API call failed", "data": None},
        )
