import google.generativeai as genai
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_gemini_synopsis(company_data: dict) -> str:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    prompt = (
        "Generate a concise, insightful business synopsis for the following Indian company. "
        "Focus on compliance, age, business health, GST activity, and risk. "
        "Write in 120-200 words, professional tone. Data:\n"
        f"{company_data}"
    )
    response = model.generate_content(prompt)
    return response.text