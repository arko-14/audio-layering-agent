"""
Groq API Client for LLM-Powered Agents
======================================

Provides a simple interface to the Groq cloud API for JSON-structured
LLM responses. Used by vibe_director, sfx_designer, and explainer agents
to make decisions based on video analysis.

Groq offers fast inference on Llama models with a generous free tier,
making it ideal for this application.

Required Environment Variable:
    GROQ_API_KEY: Your Groq API key (get one at console.groq.com)
"""
import os
import json
import requests
from typing import Any, Dict, Optional

# Groq uses OpenAI-compatible API format
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def groq_chat_json(
    system: str,
    user: str,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.2,
    max_tokens: int = 800,
    schema_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a chat completion request to Groq and parse JSON response.
    
    Args:
        system: System prompt defining the LLM's role and constraints
        user: User message with context and specific request
        model: Groq model ID (default: llama-3.3-70b-versatile)
        temperature: Randomness (0.0-1.0, lower = more deterministic)
        max_tokens: Maximum response length
        schema_hint: Optional JSON schema example to guide output format
    
    Returns:
        Dict parsed from LLM's JSON response
    
    Raises:
        RuntimeError: If GROQ_API_KEY is not set
        requests.HTTPError: If API request fails
        json.JSONDecodeError: If response is not valid JSON
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    # Append schema hint to help LLM structure its response
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