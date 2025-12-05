import httpx
from dotenv import load_dotenv
import os
 
load_dotenv()
 
# LLM Settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"
GROQ_MODEL = os.getenv("GROQ_MODEL")
 
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
 
def build_llm_prompt(raw_text: str) -> str:
    """
    Build LLM prompt for extracting clean resume text.
    """
    return f"""
You are a resume parsing assistant.
 
Extract structured data with these sections:
PERSONAL INFORMATION
SUMMARY
SKILLS
EXPERIENCE
EDUCATION
PROJECTS
 
Rules:
- Plain text only
- No JSON
- No Markdown formatting
 
Resume Content:
----------------
{raw_text}
----------------
"""
 
 
async def parse_resume_with_llm(raw_text: str) -> str:
    print("API Key:", GROQ_API_KEY)
    print("LLM Enabled:", LLM_ENABLED)
    print("GROQ Model:", GROQ_MODEL)    
    """
    Send extracted resume text to Groq LLM and return parsed text.
    """
    print("Hello in the LLm", raw_text)
 
    if not LLM_ENABLED or not GROQ_API_KEY:
        return "LLM disabled or missing API key."
 
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You parse resumes into clean sections."},
            {"role": "user", "content": build_llm_prompt(raw_text)}
        ],
        "temperature": 0.2
    }
 
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
 
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{GROQ_BASE_URL}/chat/completions",
            json=payload,
            headers=headers
        )
 
        resp.raise_for_status()
        data = resp.json()
 
        return data["choices"][0]["message"]["content"]
 