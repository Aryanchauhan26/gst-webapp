import openai
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set!")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def get_openai_synopsis(company_data: dict) -> str:
    prompt = (
        "Generate a concise, insightful business synopsis for the following Indian company. "
        "Focus on compliance, age, business health, GST activity, and risk. "
        "Write in 120-200 words, professional tone. Data:\n"
        f"{company_data}"
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()