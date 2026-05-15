import os
import json
import logging
import requests

logger = logging.getLogger("PromptGenerator")

def generate_scene_prompts(topic: str, script: str, count: int = 6) -> list[str]:
    """Gemini'ye OpenAI protokolü üzerinden ve tüm anahtarları deneyerek bağlanır."""
    
    # Tüm potansiyel anahtarları topla
    keys = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 10)]
    keys = [k for k in keys if k]
    if os.getenv("GEMINI_API_KEY"):
        keys.insert(0, os.getenv("GEMINI_API_KEY"))
    
    if not keys:
        logger.error("Hiçbir GEMINI_API_KEY bulunamadı!")
        return _get_fallback_prompts(topic, count)

    system_prompt = f"You are a cinematic director. Topic: {topic}. Generate {count} scene prompts as a JSON array."

    for api_key in keys:
        # Google'ın OpenAI uyumlu endpoint'ini kullanıyoruz (En stabil yöntem)
        # Bu yöntem 404 hatalarını ve kütüphane çakışmalarını baypas eder.
        url = f"https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gemini-1.5-flash",
            "messages": [{"role": "user", "content": system_prompt}],
            "response_format": {"type": "json_object"}
        }

        try:
            logger.info(f"[PromptGen] Anahtar deneniyor (...{api_key[-5:]})")
            r = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if r.status_code == 200:
                data = r.json()
                content = data['choices'][0]['message']['content']
                prompts_obj = json.loads(content)
                # JSON yapısına göre ayıkla
                if isinstance(prompts_obj, dict):
                    # Eğer Gemini 'prompts': [...] şeklinde dönerse
                    for val in prompts_obj.values():
                        if isinstance(val, list): return val[:count]
                if isinstance(prompts_obj, list):
                    return prompts_obj[:count]
                logger.info(f"[PromptGen] ✅ Başarıyla üretildi.")
                return list(prompts_obj)[:count]
            else:
                logger.warning(f"[PromptGen] HTTP {r.status_code}: {r.text[:100]}")
        except Exception as e:
            logger.debug(f"[PromptGen] Hata: {e}")
            continue

    logger.warning("[PromptGen] Tüm anahtarlar başarısız oldu, fallback.")
    return _get_fallback_prompts(topic, count)

def _get_fallback_prompts(topic: str, count: int) -> list[str]:
    # ... (Aynı fallback mantığı)
    FALLBACKS = {
        "battery": [
            "Extreme macro shot of glowing lithium battery cells with blue energy pulses, 8K cinematic lighting",
            "Automated electric vehicle battery assembly line with robotic arms and blue laser sparks",
            "Holographic display showing battery charge percentage increasing, futuristic lab background",
            "Close up of an EV charging port with glowing blue light reflections on wet pavement at night",
            "Solid state battery architecture visualization with electric currents flowing through crystals",
            "Futuristic energy storage facility with walls of glowing power cells, cinematic wide shot"
        ],
        "default": [
            "Cinematic shot of a futuristic electric car driving through a neon city at night, rain reflections",
            "High tech laboratory with researchers working on advanced energy systems, blue ambient light",
            "Aerial drone shot of a vast solar farm during golden hour, cinematic 4K",
            "Abstract visualization of clean energy flowing through a digital smart city grid",
            "Futuristic robotic hand holding a glowing energy core, mechanical detail, 8K",
            "Sleek electric vehicle interior with large glowing dashboard screens and ambient lighting"
        ]
    }
    key = "battery" if "battery" in topic.lower() else "default"
    return FALLBACKS[key][:count]
