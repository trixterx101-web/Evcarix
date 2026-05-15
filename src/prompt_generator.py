import os
import json
import logging
import requests

logger = logging.getLogger("PromptGenerator")

def generate_scene_prompts(topic: str, script: str, count: int = 6) -> list[str]:
    """Hataları açıkça loglayan sinematik kurgu motoru."""
    
    # ── 1. GEMINI ──
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            r = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json={
                "model": "gemini-1.5-flash",
                "messages": [{"role": "user", "content": f"JSON list of {count} scene prompts for: {topic}"}],
                "response_format": {"type": "json_object"}
            }, timeout=15)
            if r.status_code == 200:
                return _parse_json_list(r.json()['choices'][0]['message']['content'], count)
            else:
                logger.error(f"[PromptGen] Gemini Hata {r.status_code}: {r.text}")
        except Exception as e: logger.error(f"[PromptGen] Gemini İstisna: {e}")

    # ── 2. GROQ ──
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={
                "Authorization": f"Bearer {groq_key}"}, json={
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": f"JSON list of {count} scene prompts for: {topic}"}]
            }, timeout=15)
            if r.status_code == 200:
                return _parse_json_list(r.json()['choices'][0]['message']['content'], count)
            else:
                logger.error(f"[PromptGen] Groq Hata {r.status_code}: {r.text}")
        except Exception as e: logger.error(f"[PromptGen] Groq İstisna: {e}")

    return _get_fallback_prompts(topic, count)

def _parse_json_list(text, count):
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list): return v[:count]
        if isinstance(data, list): return data[:count]
    except: pass
    return None

def _get_fallback_prompts(topic: str, count: int) -> list[str]:
    # ... (Aynı fallback'ler)
    return ["A cinematic view of electric vehicle battery technology, 8K"] * count
