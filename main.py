from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import os

app = FastAPI()

# Read API key from environment variable for security
API_KEY = os.getenv("API_KEY", "Kx2P5PaBsWburrwNCCaX3rKF7YQ2")

# Mount static and templates directories
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "data": None, "error": None})

@app.post("/", response_class=HTMLResponse)
def fetch_gst_data(request: Request, gstin: str = Form(...)):
    url = f"https://appyflow.in/api/verifyGST?gstNo={gstin}&key_secret={API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()

        if "error" in data:
            return templates.TemplateResponse("index.html", {"request": request, "error": data["error"], "data": None})

        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": {
                "legalName": data.get("legalName"),
                "tradeName": data.get("tradeName"),
                "address": data.get("address"),
                "state": data.get("stateJurisdiction"),
                "status": data.get("gstinStatus")
            },
            "error": None
        })
    
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "API request failed. Please try again.",
            "data": None
        })

