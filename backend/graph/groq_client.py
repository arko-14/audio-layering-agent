import os
import json
import requests
from typing import Any, Dict, Optional

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def groq_chat_json(
    system: str,
    user: str,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.2,
    max_tokens: int = 800,
    schema_hint: Optional[str] = None,
) -> Dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    if schema_hint:
        user = user + "\n\nReturn ONLY valid JSON.\nSchema:\n" + schema_hint

    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }

    r = requests.post(
        GROQ_API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=90,
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    return json.loads(content)