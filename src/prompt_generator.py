import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger("PromptGenerator")

def generate_scene_prompts(topic: str, script: str, count: int = 6) -> list[str]:
    """Gemini kullanarak sinematik video sahneleri tasarlar. Akıllı model seçici içerir."""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY eksik!")
        return _get_fallback_prompts(topic, count)

    genai.configure(api_key=api_key)
    
    # Denenecek model isimleri (Öncelik sırasına göre)
    model_candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-pro",
        "models/gemini-1.5-flash"
    ]

    system_prompt = f"""You are a cinematic video director for YouTube Shorts.
Topic: {topic}
Script: {script[:500]}

Generate exactly {count} different cinematic video scene prompts.
Format: JSON array of strings.
Style: Photorealistic, 4K, cinematic lighting, no text."""

    success_text = None
    
    for model_name in model_candidates:
        try:
            logger.info(f"[PromptGen] Deneniyor: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(system_prompt)
            if response and response.text:
                success_text = response.text.strip()
                logger.info(f"[PromptGen] ✅ {model_name} ile başarıyla üretildi.")
                break
        except Exception as e:
            logger.warning(f"[PromptGen] {model_name} başarısız: {str(e)[:100]}")
            continue

    if success_text:
        try:
            # JSON temizleme
            if "```" in success_text:
                success_text = success_text.split("```")[1].replace("json", "").strip()
            
            prompts = json.loads(success_text)
            if isinstance(prompts, list) and len(prompts) >= count:
                return prompts[:count]
        except Exception as e:
            logger.error(f"JSON Parse hatası: {e}")

    return _get_fallback_prompts(topic, count)

def _get_fallback_prompts(topic: str, count: int) -> list[str]:
    """Tüm modeller başarısız olursa konu bazlı hazır kaliteli promptlar döner."""
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
