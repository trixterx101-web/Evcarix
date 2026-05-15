import os
import json
import logging
from google import genai

logger = logging.getLogger("PromptGenerator")

def generate_scene_prompts(topic: str, script: str, count: int = 6) -> list[str]:
    """Yeni google-genai SDK'sını kullanarak sahneleri kurgular."""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            logger.info("[PromptGen] Yeni Gemini SDK (genai) deneniyor...")
            client = genai.Client(api_key=api_key)
            
            prompt_text = f"Director: Generate exactly {count} cinematic scene descriptions for a video about '{topic}'. Return ONLY a JSON array of strings."
            
            # Yeni SDK'da model ismi v1beta gibi ekler gerektirmez
            response = client.models.generate_content(
                model="gemini-2.0-flash", # En hızlı ve yeni model
                contents=prompt_text
            )
            
            if response and response.text:
                res = _parse_json_list(response.text, count)
                if res: return res
        except Exception as e:
            logger.error(f"[PromptGen] Yeni SDK Hatası: {e}")

    # Fallback her zaman devrededir
    return _get_fallback_prompts(topic, count)

def _parse_json_list(text, count):
    try:
        # JSON olmayan kısımları temizle
        clean_text = text.strip()
        if "```" in clean_text:
            clean_text = clean_text.split("```")[1]
            if clean_text.startswith("json"): clean_text = clean_text[4:]
        
        data = json.loads(clean_text.strip())
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list): return [str(x) for x in v[:count]]
        if isinstance(data, list): return [str(x) for x in data[:count]]
    except: pass
    return None

def _get_fallback_prompts(topic: str, count: int) -> list[str]:
    base = [
        "Cinematic slow motion shot of an electric car driving on a coastal road, golden hour",
        "Extreme close up of a futuristic EV dashboard with glowing blue lights",
        "Aerial view of a modern charging station in a green city, 4K cinematic",
        "Macro shot of lithium battery cells with electric blue energy flowing",
        "Sleek electric vehicle interior with large panoramic glass roof",
        "Minimalist visualization of electric power lines connecting to a smart car"
    ]
    result = []
    for i in range(count):
        result.append(base[i % len(base)])
    return result
