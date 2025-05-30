import os
import google.generativeai as genai

# Set up Gemini API key
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable not found.")

genai.configure(api_key=API_KEY)

# Initialize the model (adjust model name if needed)
model = genai.GenerativeModel("gemini-1.5-pro")

def get_gemini_synopsis(company_data: dict) -> str:
    prompt = (
        "Generate a concise, insightful business synopsis for the following Indian company. "
        "Focus on compliance, age, business health, GST activity, and risk. "
        "Write in 120-200 words, professional tone. Data:\n"
        f"{company_data}"
    )
    response = model.generate_content(prompt)
    return response.text.strip()