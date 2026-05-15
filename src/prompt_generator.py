import os
import json
import logging
import requests

logger = logging.getLogger("PromptGenerator")

def generate_scene_prompts(topic: str, script: str, count: int = 6) -> list[str]:
    """Sinematik sahneleri kurgular. Hata toleransı en üst seviyededir."""
    
    # Tüm LLM'leri dene
    res = _try_gemini(topic, count)
    if res: return res
    
    res = _try_groq(topic, count)
    if res: return res

    logger.warning("[PromptGen] Yapay zekalar cevap vermedi, fallback'e geçiliyor.")
    return _get_fallback_prompts(topic, count)

def _try_gemini(topic, count):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return None
    try:
        url = "https://generativelanguage.googleapis.com/v1/openai/chat/completions"
        r = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json={
            "model": "gemini-1.5-flash",
            "messages": [{"role": "user", "content": f"JSON list of {count} strings describing cinematic video scenes for: {topic}"}],
            "response_format": {"type": "json_object"}
        }, timeout=15)
        if r.status_code == 200:
            return _parse_json_list(r.json()['choices'][0]['message']['content'], count)
    except: pass
    return None

def _try_groq(topic, count):
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key: return None
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={
            "Authorization": f"Bearer {groq_key}"}, json={
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": f"JSON list of {count} cinematic scene descriptions for: {topic}"}]
        }, timeout=15)
        if r.status_code == 200:
            return _parse_json_list(r.json()['choices'][0]['message']['content'], count)
    except: pass
    return None

def _parse_json_list(text, count):
    try:
        if "```" in text: text = text.split("```")[1].replace("json", "").strip()
        data = json.loads(text.strip())
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list): return [str(x) for x in v[:count]]
        if isinstance(data, list): return [str(x) for x in data[:count]]
    except: pass
    return None

def _get_fallback_prompts(topic: str, count: int) -> list[str]:
    """Asla hata vermeyen, garanti listeyi oluşturur."""
    base = [
        "Cinematic slow motion shot of an electric car driving on a coastal road, golden hour",
        "Extreme close up of a futuristic EV dashboard with glowing blue lights",
        "Aerial view of a modern charging station in a green city, 4K cinematic",
        "Macro shot of lithium battery cells with electric blue energy flowing",
        "Sleek electric vehicle interior with large panoramic glass roof",
        "Minimalist visualization of electric power lines connecting to a smart car"
    ]
    # Listeyi istenen sayıya güvenli bir şekilde tamamla (Çarpma yerine döngü)
    result = []
    for i in range(count):
        result.append(base[i % len(base)])
    return result
