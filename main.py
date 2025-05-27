from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import httpx

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

RAPIDAPI_KEY = "08cbf9855dmsh5c8d8660645305cp1a8713jsn17eca3b207a5"
RAPIDAPI_HOST = "gst-return-status.p.rapidapi.com"
BASE_URL = "https://gst-return-status.p.rapidapi.com/free/gstin/"

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "data": None, "error": None})

@app.post("/", response_class=HTMLResponse)
async def fetch_gst_data(request: Request, gstin: str = Form(...)):
    gstin = gstin.upper()
    url = f"{BASE_URL}{gstin}"

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            result = response.json()
            if result.get("success"):
                return templates.TemplateResponse("index.html", {
                    "request": request,
                    "data": result["data"],
                    "error": None
                })
            else:
                return templates.TemplateResponse("index.html", {
                    "request": request,
                    "data": None,
                    "error": "No data found for this GSTIN."
                })
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": f"Error: {str(e)}"
        })

@app.post("/rate", response_class=HTMLResponse)
async def rate_company(request: Request, gstin: str = Form(...)):
    gstin = gstin.upper()
    url = f"{BASE_URL}{gstin}"

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            result = response.json()

        if not result.get("success"):
            raise ValueError("No data found for this GSTIN.")

        data = result["data"]
        returns = data.get("returns", [])

        on_time_count = len(returns)
        status = data.get("sts", "").lower()
        category = data.get("compCategory", "")

        # Rating logic
        if status == "active" and on_time_count >= 18:
            rating = "A+ (Excellent Compliance)"
        elif status == "active" and on_time_count >= 12:
            rating = "A (Good Compliance)"
        elif status == "active":
            rating = "B (Moderate Compliance)"
        else:
            rating = "C (Inactive or Poor Compliance)"

        return templates.TemplateResponse("rate.html", {
            "request": request,
            "gstin": gstin,
            "company": data.get("lgnm"),
            "status": status.title(),
            "returns_filed": on_time_count,
            "rating": rating
        })

    except Exception as e:
        return templates.TemplateResponse("rate.html", {
            "request": request,
            "gstin": gstin,
            "error": f"Error: {str(e)}"
        })
