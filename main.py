@app.post("/", response_class=HTMLResponse)
def fetch_gst_data(request: Request, gstin: str = Form(...)):
    url = f"https://appyflow.in/api/verifyGST?gstNo={gstin}&key_secret={API_KEY}"
    
    print(f"Fetching GST details for: {gstin}")
    print(f"API URL: {url}")

    try:
        response = requests.get(url)
        data = response.json()
        print("API Response:", data)

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
        print("Exception:", e)
        return templates.TemplateResponse("index.html", {"request": request, "error": "API call failed", "data": None})
