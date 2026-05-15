import os
import json
import logging
import requests

logger = logging.getLogger("PromptGenerator")

def generate_scene_prompts(topic: str, script: str, count: int = 6) -> list[str]:
    """Sahneleri kurgulamak için 3 farklı yapay zeka servisini sırayla dener."""
    
    # ── 1. ADIM: GEMINI (OpenAI Protokolü üzerinden) ──
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            logger.info("[PromptGen] Gemini deneniyor...")
            url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            r = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json={
                "model": "gemini-1.5-flash",
                "messages": [{"role": "user", "content": f"Director: Generate {count} cinematic video scene prompts for {topic} as JSON array."}],
                "response_format": {"type": "json_object"}
            }, timeout=15)
            if r.status_code == 200:
                content = r.json()['choices'][0]['message']['content']
                return _parse_json_list(content, count)
        except: pass

    # ── 2. ADIM: GROQ (Llama 3 - Ultra Hızlı Yedek) ──
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            logger.info("[PromptGen] Gemini başarısız, Groq (Llama 3) deneniyor...")
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={
                "Authorization": f"Bearer {groq_key}"}, json={
                "model": "llama3-70b-8192",
                "messages": [{"role": "user", "content": f"As a video director, generate exactly {count} cinematic scene prompts for a video about '{topic}'. Return ONLY a JSON array of strings."}],
                "response_format": {"type": "json_object"}
            }, timeout=15)
            if r.status_code == 200:
                content = r.json()['choices'][0]['message']['content']
                return _parse_json_list(content, count)
        except: pass

    # ── 3. ADIM: OPENROUTER (Son Çare) ──
    or_key = os.getenv("OPENROUTER_API_KEY")
    if or_key:
        try:
            logger.info("[PromptGen] OpenRouter deneniyor...")
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={
                "Authorization": f"Bearer {or_key}"}, json={
                "model": "meta-llama/llama-3-8b-instruct:free",
                "messages": [{"role": "user", "content": f"Generate {count} video scene prompts for {topic} as JSON array."}]
            }, timeout=15)
            if r.status_code == 200:
                content = r.json()['choices'][0]['message']['content']
                return _parse_json_list(content, count)
        except: pass

    logger.warning("[PromptGen] Tüm yapay zekalar başarısız, sabit fallback sahneleri yükleniyor.")
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
        "battery": [
            "Extreme macro shot of glowing lithium battery cells, blue energy pulses, 8K",
            "Automated EV battery assembly line with robotic arms, blue lighting",
            "Holographic display showing battery charge increasing, tech background",
            "Close up of an EV charging port with glowing blue light at night",
            "Solid state battery crystal structure visualization, electric blue",
            "Futuristic energy storage facility with glowing walls, wide shot"
        ],
        "default": [
            "Cinematic futuristic electric car driving through neon city, rain reflections",
            "High tech lab with researchers working on advanced energy systems",
            "Aerial drone shot of a vast solar farm during golden hour, 4K",
            "Abstract visualization of clean energy flowing through smart city grid",
            "Futuristic robotic hand holding a glowing energy core, 8K",
            "Sleek EV interior with glowing dashboard screens and ambient light"
        ]
    }
    key = "battery" if "battery" in topic.lower() else "default"
    return FALLBACKS[key][:count]
