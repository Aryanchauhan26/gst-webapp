from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

RAPIDAPI_KEY = "08cbf9855dmsh5c8d8660645305cp1a8713jsn17eca3b207a5"
RAPIDAPI_HOST = "gst-insights-api.p.rapidapi.com"

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "data": None, "error": None})

@app.post("/", response_class=HTMLResponse)
def fetch_gst_data(request: Request, gstin: str = Form(...)):
    url = f"https://{RAPIDAPI_HOST}/getGSTDetailsUsingGST/{gstin}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        print("API Response:", data)

        if not data.get("success"):
            return templates.TemplateResponse("index.html", {
                "request": request,
                "error": data.get("message", "Invalid GSTIN or API error."),
                "data": None
            })

        gst_data = data["data"]
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": {
                "legalName": gst_data.get("lgnm"),
                "tradeName": gst_data.get("tradeName"),
                "address": gst_data.get("adr"),
                "state": gst_data.get("stj"),
                "status": gst_data.get("sts")
            },
            "error": None
        })

    except Exception as e:
        print("Exception:", e)
        return templates.TemplateResponse("index.html", {"request": request, "error": "API call failed", "data": None})
