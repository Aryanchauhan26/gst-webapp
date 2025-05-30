import os
import google.generativeai as genai

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable not found.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro")

def get_minimal_company_data(data: dict) -> dict:
    # Only keep essentials; adjust as needed for your logic
    return {
        "name": data.get("lgnm"),
        "gstin": data.get("gstin"),
        "status": data.get("sts"),
        "compliance": data.get("compliance", {}),
        "recent_returns": data.get("returns", [])[:2],  # Only 2 most recent
    }

def get_gemini_synopsis(company_data: dict) -> str:
    minimal_data = get_minimal_company_data(company_data)
    prompt = (
        "Generate a concise Indian business synopsis (120-200 words) focusing on compliance, age, business health, and risk. Data:\n"
        f"{minimal_data}"
    )
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Handle quota exceeded or other Gemini errors gracefully
        return ("[Gemini AI Error] Unable to generate synopsis at the moment. "
                "You may have exceeded your free quota. Please try again later or reduce usage.")