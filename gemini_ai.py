import google.generativeai as genai
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set!")

def get_gemini_synopsis(company_data: dict) -> str:
    genai.configure(api_key=GEMINI_API_KEY)
    # Use the correct model name!
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    prompt = (
        "Generate a concise, insightful business synopsis for the following Indian company. "
        "Focus on compliance, age, business health, GST activity, and risk. "
        "Write in 120-200 words, professional tone. Data:\n"
        f"{company_data}"
    )
    response = model.generate_content(prompt)
    return response.text