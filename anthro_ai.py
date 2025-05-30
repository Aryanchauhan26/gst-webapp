import os
import anthropic

def get_anthropic_synopsis(company_data: dict) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    minimal_data = {
        "name": company_data.get("lgnm"),
        "gstin": company_data.get("gstin"),
        "status": company_data.get("sts"),
        "compliance": company_data.get("compliance", {}),
        "recent_returns": company_data.get("returns", [])[:2],
    }
    prompt = (
        "Generate a concise Indian business synopsis (120-200 words) focusing on compliance, age, business health, and risk. "
        "Here's the company data:\n"
        f"{minimal_data}"
    )
    try:
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=512,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except Exception as e:
        return "[Anthropic Error] Unable to generate synopsis. Please check your API limits or key."