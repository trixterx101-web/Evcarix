import os
import json
import logging
import requests

logger = logging.getLogger("PromptGenerator")

def generate_scene_prompts(topic: str, script: str, count: int = 6) -> list[str]:
    """Hataları giderilmiş, güncel modelleri kullanan kurgu motoru."""
    
    # ── 1. GEMINI (v1 Stabil Hattı) ──
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            # v1beta yerine v1 kullanarak 404 hatasını kalıcı olarak aşıyoruz
            url = "https://generativelanguage.googleapis.com/v1/openai/chat/completions"
            r = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json={
                "model": "gemini-1.5-flash",
                "messages": [{"role": "user", "content": f"Director: Generate {count} cinematic scene prompts for {topic} as a JSON array of strings."}],
                "response_format": {"type": "json_object"}
            }, timeout=15)
            if r.status_code == 200:
                return _parse_json_list(r.json()['choices'][0]['message']['content'], count)
            else:
                logger.error(f"[PromptGen] Gemini Hata {r.status_code}: {r.text}")
        except: pass

    # ── 2. GROQ (Llama 3.1 - En Yeni Versiyon) ──
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            # Emekli edilen model yerine llama-3.1-8b-instant kullanıyoruz
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={
                "Authorization": f"Bearer {groq_key}"}, json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": f"JSON list of {count} scene prompts for: {topic}"}]
            }, timeout=15)
            if r.status_code == 200:
                return _parse_json_list(r.json()['choices'][0]['message']['content'], count)
            else:
                logger.error(f"[PromptGen] Groq Hata {r.status_code}: {r.text}")
        except: pass

    return _get_fallback_prompts(topic, count)

def _parse_json_list(text, count):
    try:
        if "```" in text: text = text.split("```")[1].replace("json", "").strip()
        data = json.loads(text)
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list): return v[:count]
        if isinstance(data, list): return data[:count]
    except: pass
    return None

def _get_fallback_prompts(topic: str, count: int) -> list[str]:
    FALLBACKS = {
        "battery": ["Extreme macro shot of glowing lithium battery cells, blue pulses, 8K"] * count,
        "default": ["Cinematic futuristic electric car driving through neon city, 4K"] * count
    }
    key = "battery" if "battery" in topic.lower() else "default"
    return FALLBACKS[key][:count]
