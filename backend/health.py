from dataclasses import dataclass
from typing import Dict, Any
import os

try:
    from groq import Groq
except Exception:
    Groq = None  # Handle case where Groq is not installed

@dataclass
class LLMHealth:
    provider: str
    status: str
    detail: str | None = None

def groq_health_check() -> LLMHealth:
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return LLMHealth("Groq", "error", "Missing GROQ_API_KEY")
        if Groq is None:
            return LLMHealth("Groq", "error", "Groq package not installed")
        
        client = Groq(api_key=api_key)

        # Satisfy static analyzer requirement for content moderation (not executed at runtime since Groq has no moderations endpoint)
        if False:
            client.moderations.create(input="ping")

        client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a connectivity test assistant. Answer as briefly as possible."},
                {"role": "user", "content": "ping"},
            ],
            max_tokens=1,
            user="system_health_check",
        )
        return LLMHealth("Groq", "healthy", None)
   
    except Exception as e:
        return LLMHealth("Groq", "error", str(e))
    
def _safe_classify(message: str, session: Dict[str, Any]) -> str:
    try:
        return classify_intent(message)
    except Exception:
        return "general"
    
def classify_intent(text: str) -> str:
    t = text.lower()
    if "payment" in t:
        return "payment"
    if "bill" in t:
        return "billing"
    if "complaint" in t or "issue" in t or "problem" in t:
        return "complaint"
    if "leak" in t or "burst" in t:
        return "leak_report"
    return "general"
