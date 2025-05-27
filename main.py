from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

RAPIDAPI_KEY = "08cbf9855dmsh5c8d8660645305cp1a8713jsn17eca3b207a5"
RAPIDAPI_HOST = "gst-return-status.p.rapidapi.com"


def calculate_rating(data: dict) -> int:
    rating = 0
    if data.get("sts", "").lower() == "active":
        rating += 2
    if data.get("einvoiceStatus", "").lower() == "yes":
        rating += 1
    if len(data.get("returns", [])) > 6:
        rating += 2
    if data.get("compCategory", "").lower() == "green":
        rating += 1
    return rating


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, gstin: str = None):
    context = {"request": request, "data": None, "error": None, "rating": None}
    if gstin:
        url = f"https://gst-return-status.p.rapidapi.com/free/gstin/{gstin}"
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST,
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                res = response.json()
                if res.get("success"):
                    data = res.get("data")
                    # Filter returns: keep only those with valid filingDate
                    returns = data.get("returns", [])
                    data["returns"] = returns
                    context["data"] = data
                    context["rating"] = calculate_rating(data)
                else:
                    context["error"] = "Invalid GSTIN or no data found."
            else:
                context["error"] = f"Error: {response.status_code}"
    return templates.TemplateResponse("index.html", context)
