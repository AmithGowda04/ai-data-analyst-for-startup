"""Gemini call with timeout, retry on transient errors, and model fallback."""
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv(override=True)
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=os.environ["LLM_API_KEY"],
            http_options=types.HttpOptions(timeout=30000),
        )
    return _client


def _models():
    primary = os.environ.get("LLM_MODEL", "").strip()
    fallbacks = [m.strip() for m in os.environ.get("LLM_FALLBACK_MODELS", "").split(",")]
    return [m for m in [primary] + fallbacks if m]


def generate(system, prompt, retries=3):
    """Return (text, model_used)."""
    cfg = types.GenerateContentConfig(system_instruction=system, temperature=0)
    last = None
    for model in _models():
        for attempt in range(retries):
            try:
                r = _get_client().models.generate_content(model=model, contents=prompt, config=cfg)
                return r.text or "", model
            except errors.APIError as e:
                last = e
                if e.code in (429, 500, 503, 504):
                    time.sleep(2 ** attempt)
                    continue
                break
            except Exception as e:
                last = e
                time.sleep(2 ** attempt)
    raise RuntimeError(f"All models failed. Last error: {last}")